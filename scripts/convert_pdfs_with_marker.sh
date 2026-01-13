#!/bin/bash
# convert_pdfs_with_marker.sh
#
# Convert PDF files in project_pdfs directory to Markdown using Marker
# https://github.com/datalab-to/marker
#
# Usage:
#   ./scripts/convert_pdfs_with_marker.sh [project_name] [marker_options...]
#
# Examples:
#   # Process all projects with default settings
#   ./scripts/convert_pdfs_with_marker.sh
#
#   # Process specific project
#   ./scripts/convert_pdfs_with_marker.sh my_project
#
#   # Use LLM services for better extraction (OpenAI example)
#   ./scripts/convert_pdfs_with_marker.sh my_project --llm_provider openai --llm_model gpt-4o
#
#   # Use specific language for OCR
#   ./scripts/convert_pdfs_with_marker.sh --langs English
#
#   # Combine multiple options
#   ./scripts/convert_pdfs_with_marker.sh my_project --llm_provider anthropic --llm_model claude-3-5-sonnet-20241022 --langs English
#
# Environment Variables for LLM API Keys:
#   The script supports provider-specific environment variables that are securely
#   passed to Marker via environment (not command-line arguments) to avoid exposure
#   in process listings and logs:
#
#   OpenAI:
#     MARKER_OPENAI_API_KEY        → exported as OPENAI_API_KEY
#
#   Anthropic:
#     MARKER_ANTHROPIC_API_KEY     → exported as ANTHROPIC_API_KEY
#
#   Google Gemini:
#     MARKER_GEMINI_API_KEY        → exported as GEMINI_API_KEY
#
#   Google Vertex AI:
#     MARKER_VERTEX_PROJECT_ID     → exported as VERTEX_PROJECT_ID
#     MARKER_VERTEX_LOCATION       → exported as VERTEX_LOCATION
#     MARKER_VERTEX_MODEL          → exported as VERTEX_MODEL
#
#   Ollama:
#     MARKER_OLLAMA_BASE_URL       → exported as OLLAMA_BASE_URL
#
#   Generic (backwards compatible):
#     MARKER_LLM_API_KEY           → exported as LLM_API_KEY
#
#   Security Note: API keys are passed via environment variables (not CLI arguments)
#   to prevent exposure in process listings. The script validates path inputs and
#   redacts sensitive data from error logs.
#
# Prerequisites:
#   - marker-pdf installed: pip install marker-pdf
#   - project_pdfs directory exists with PDF files
#   - For LLM services: Set appropriate MARKER_* environment variables
#
# Output:
#   - Markdown files will be created in project_markdowns directory
#   - Directory structure mirrors project_pdfs
#
# Supported Marker Options (pass as CLI arguments):
#   --llm_provider <provider>    LLM provider (openai, anthropic, google, etc.)
#   --llm_model <model>          Specific LLM model to use
#   --langs <language>           Language(s) for OCR (e.g., English, Spanish)
#   --batch_multiplier <num>     Process multiple PDFs in parallel
#   --workers <num>              Number of worker processes
#   And other marker CLI options - pass them after the project name
#
#   Note: For security, API keys should be set via MARKER_* environment variables
#   rather than passed as CLI arguments.
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Global variable for temp file (used in trap)
TEMP_ERROR_LOG=""

# Cleanup function for temporary files
cleanup_temp_files() {
    if [ -n "${TEMP_ERROR_LOG}" ] && [ -f "${TEMP_ERROR_LOG}" ]; then
        rm -f "${TEMP_ERROR_LOG}"
    fi
}

# Set up trap to cleanup on exit or interruption
trap cleanup_temp_files EXIT INT TERM

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PDF_DIR="${REPO_ROOT}/project_pdfs"
MARKDOWN_DIR="${REPO_ROOT}/project_markdowns"

# Additional marker options (passed as arguments)
MARKER_EXTRA_OPTS=""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to export environment variables for Marker
# This avoids exposing API keys in process listings and logs
# Instead of passing --api_key "secret" on command line, we export env vars
# that Marker CLI will read directly
setup_marker_environment() {
    # OpenAI
    if [ -n "${MARKER_OPENAI_API_KEY:-}" ]; then
        export OPENAI_API_KEY="${MARKER_OPENAI_API_KEY}"
    fi
    
    # Anthropic
    if [ -n "${MARKER_ANTHROPIC_API_KEY:-}" ]; then
        export ANTHROPIC_API_KEY="${MARKER_ANTHROPIC_API_KEY}"
    fi
    
    # Google Gemini
    if [ -n "${MARKER_GEMINI_API_KEY:-}" ]; then
        export GEMINI_API_KEY="${MARKER_GEMINI_API_KEY}"
    fi
    
    # Google Vertex AI
    if [ -n "${MARKER_VERTEX_PROJECT_ID:-}" ]; then
        export VERTEX_PROJECT_ID="${MARKER_VERTEX_PROJECT_ID}"
    fi
    if [ -n "${MARKER_VERTEX_LOCATION:-}" ]; then
        export VERTEX_LOCATION="${MARKER_VERTEX_LOCATION}"
    fi
    if [ -n "${MARKER_VERTEX_MODEL:-}" ]; then
        export VERTEX_MODEL="${MARKER_VERTEX_MODEL}"
    fi
    
    # Ollama
    if [ -n "${MARKER_OLLAMA_BASE_URL:-}" ]; then
        export OLLAMA_BASE_URL="${MARKER_OLLAMA_BASE_URL}"
    fi
    
    # Generic LLM API key (backwards compatible)
    if [ -n "${MARKER_LLM_API_KEY:-}" ]; then
        export LLM_API_KEY="${MARKER_LLM_API_KEY}"
    fi
}

# Function to check if marker-pdf is installed
check_marker_installed() {
    if ! command -v marker &> /dev/null; then
        log_error "marker-pdf is not installed or not in PATH"
        log_info "Install with: pip install marker-pdf"
        log_info "See: https://github.com/datalab-to/marker"
        exit 1
    fi
    log_success "marker-pdf is installed"
}

# Function to check if project_pdfs directory exists
check_pdf_directory() {
    if [ ! -d "$PDF_DIR" ]; then
        log_error "PDF directory not found: $PDF_DIR"
        log_info "Please ensure project_pdfs directory exists with PDF files"
        exit 1
    fi
    log_success "PDF directory found: $PDF_DIR"
}

# Function to create markdown output directory
create_markdown_directory() {
    if [ ! -d "$MARKDOWN_DIR" ]; then
        log_info "Creating markdown directory: $MARKDOWN_DIR"
        mkdir -p "$MARKDOWN_DIR"
    fi
    log_success "Markdown directory ready: $MARKDOWN_DIR"
}

# Function to convert a single PDF to Markdown
convert_pdf() {
    local pdf_path="$1"
    
    # Validate that pdf_path is within PDF_DIR to prevent path traversal
    local pdf_realpath
    pdf_realpath=$(realpath "$pdf_path" 2>/dev/null || echo "$pdf_path")
    local pdf_dir_realpath
    pdf_dir_realpath=$(realpath "$PDF_DIR" 2>/dev/null || echo "$PDF_DIR")
    
    if [[ ! "$pdf_realpath" =~ ^"$pdf_dir_realpath" ]]; then
        log_error "Security: PDF path is outside expected directory: $pdf_path"
        return 1
    fi
    
    local relative_path="${pdf_path#$PDF_DIR/}"
    local markdown_file="${MARKDOWN_DIR}/${relative_path%.pdf}.md"
    local markdown_subdir="$(dirname "$markdown_file")"
    
    # Create subdirectory if needed
    if [ ! -d "$markdown_subdir" ]; then
        mkdir -p "$markdown_subdir"
    fi
    
    # Skip if markdown file already exists
    if [ -f "$markdown_file" ]; then
        log_warning "Skipping (already exists): $relative_path"
        return 2  # Return special code for skipped files
    fi
    
    log_info "Converting: $relative_path"
    
    # Create secure temporary error log file
    TEMP_ERROR_LOG=$(mktemp -t marker_error.XXXXXX) || {
        log_error "Failed to create temporary error log file"
        return 1
    }
    
    # Run marker conversion with additional options using arrays (no eval)
    local output_dir
    output_dir="$(dirname "$markdown_file")"
    local output_basename
    output_basename="$(basename "${markdown_file%.md}")"
    
    # Build marker command using array to avoid eval and command injection
    local marker_cmd=(marker "$pdf_path" "$output_dir" --output_format markdown --filename "$output_basename")
    
    # Add extra options if provided (split safely into array)
    if [ -n "$MARKER_EXTRA_OPTS" ]; then
        # Read MARKER_EXTRA_OPTS into an array without using eval
        local extra_opts_array=()
        read -r -a extra_opts_array <<< "$MARKER_EXTRA_OPTS"
        marker_cmd+=("${extra_opts_array[@]}")
    fi
    
    # Execute marker command (environment variables are already exported)
    if "${marker_cmd[@]}" > /dev/null 2>"$TEMP_ERROR_LOG"; then
        log_success "Converted: $relative_path → ${relative_path%.pdf}.md"
        rm -f "$TEMP_ERROR_LOG"
        TEMP_ERROR_LOG=""
        return 0
    else
        log_error "Failed to convert: $relative_path"
        if [ -f "$TEMP_ERROR_LOG" ]; then
            # Redact potential API keys from error output before displaying
            if command -v sed >/dev/null 2>&1; then
                # Redact common API key patterns
                sed -E 's/(sk-[A-Za-z0-9]{20,})/[REDACTED_API_KEY]/g; s/(sk-ant-[A-Za-z0-9_-]{20,})/[REDACTED_API_KEY]/g; s/(AIza[A-Za-z0-9_-]{20,})/[REDACTED_API_KEY]/g' "$TEMP_ERROR_LOG" >&2
            else
                cat "$TEMP_ERROR_LOG" >&2
            fi
            rm -f "$TEMP_ERROR_LOG"
            TEMP_ERROR_LOG=""
        fi
        return 1
    fi
}

# Function to find and convert PDFs in a project
process_project() {
    local project_name="$1"
    local project_pdf_dir="${PDF_DIR}/${project_name}"
    
    if [ ! -d "$project_pdf_dir" ]; then
        log_warning "Project directory not found: $project_name"
        return 1
    fi
    
    log_info "Processing project: $project_name"
    
    # Find all PDFs in project directory
    local pdf_count=0
    local success_count=0
    local skip_count=0
    local error_count=0
    
    while IFS= read -r -d '' pdf_file; do
        ((pdf_count++))
        convert_pdf "$pdf_file"
        local result=$?
        if [ $result -eq 0 ]; then
            ((success_count++))
        elif [ $result -eq 2 ]; then
            ((skip_count++))
        else
            ((error_count++))
        fi
    done < <(find "$project_pdf_dir" -type f -name "*.pdf" -print0)
    
    log_info "Project $project_name: Found $pdf_count PDFs, Converted $success_count, Skipped $skip_count, Errors $error_count"
}

# Function to process all projects
process_all_projects() {
    log_info "Processing all projects in $PDF_DIR"
    
    # Find all subdirectories in project_pdfs
    local project_count=0
    
    for project_dir in "$PDF_DIR"/*; do
        if [ -d "$project_dir" ]; then
            local project_name="$(basename "$project_dir")"
            process_project "$project_name"
            ((project_count++))
        fi
    done
    
    if [ $project_count -eq 0 ]; then
        log_warning "No project directories found in $PDF_DIR"
        log_info "Expected structure: project_pdfs/project_name/*.pdf"
    else
        log_success "Processed $project_count projects"
    fi
}

# Main execution
main() {
    log_info "=== Marker PDF to Markdown Conversion ==="
    log_info "Repository root: $REPO_ROOT"
    
    # Parse arguments
    local project_name=""
    local remaining_args=()
    
    # First argument might be project name (if it doesn't start with --)
    if [ $# -gt 0 ] && [[ ! "$1" =~ ^-- ]]; then
        project_name="$1"
        shift
    fi
    
    # Remaining arguments are marker options
    if [ $# -gt 0 ]; then
        MARKER_EXTRA_OPTS="$*"
        log_info "Using additional Marker options: $MARKER_EXTRA_OPTS"
    fi
    
    # Show detected environment variables for LLM services and validate them
    local env_count=0
    if [ -n "${MARKER_OPENAI_API_KEY:-}" ]; then
        if [ ${#MARKER_OPENAI_API_KEY} -lt 10 ]; then
            log_warning "MARKER_OPENAI_API_KEY appears too short (< 10 chars)"
        fi
        log_info "Environment: MARKER_OPENAI_API_KEY detected"
        ((env_count++))
    fi
    if [ -n "${MARKER_ANTHROPIC_API_KEY:-}" ]; then
        if [ ${#MARKER_ANTHROPIC_API_KEY} -lt 10 ]; then
            log_warning "MARKER_ANTHROPIC_API_KEY appears too short (< 10 chars)"
        fi
        log_info "Environment: MARKER_ANTHROPIC_API_KEY detected"
        ((env_count++))
    fi
    if [ -n "${MARKER_GEMINI_API_KEY:-}" ]; then
        if [ ${#MARKER_GEMINI_API_KEY} -lt 10 ]; then
            log_warning "MARKER_GEMINI_API_KEY appears too short (< 10 chars)"
        fi
        log_info "Environment: MARKER_GEMINI_API_KEY detected"
        ((env_count++))
    fi
    if [ -n "${MARKER_VERTEX_PROJECT_ID:-}" ]; then
        log_info "Environment: MARKER_VERTEX_PROJECT_ID detected"
        ((env_count++))
    fi
    if [ -n "${MARKER_VERTEX_LOCATION:-}" ]; then
        log_info "Environment: MARKER_VERTEX_LOCATION detected"
        ((env_count++))
    fi
    if [ -n "${MARKER_VERTEX_MODEL:-}" ]; then
        log_info "Environment: MARKER_VERTEX_MODEL detected"
        ((env_count++))
    fi
    if [ -n "${MARKER_OLLAMA_BASE_URL:-}" ]; then
        log_info "Environment: MARKER_OLLAMA_BASE_URL detected"
        ((env_count++))
    fi
    if [ -n "${MARKER_LLM_API_KEY:-}" ]; then
        if [ ${#MARKER_LLM_API_KEY} -lt 10 ]; then
            log_warning "MARKER_LLM_API_KEY appears too short (< 10 chars)"
        fi
        log_info "Environment: MARKER_LLM_API_KEY detected (generic)"
        ((env_count++))
    fi
    
    if [ $env_count -eq 0 ]; then
        log_info "No LLM environment variables detected (using default Marker settings)"
    fi
    
    # Export environment variables for Marker (avoids exposing secrets in process listings)
    setup_marker_environment
    
    # Pre-flight checks
    check_marker_installed
    check_pdf_directory
    create_markdown_directory
    
    # Process PDFs
    if [ -z "$project_name" ]; then
        # No project name: process all projects
        process_all_projects
    else
        # Process specific project
        log_info "Processing specific project: $project_name"
        process_project "$project_name"
    fi
    
    log_success "=== Conversion Complete ==="
    log_info "Markdown files are in: $MARKDOWN_DIR"
}

# Run main function with all arguments
main "$@"
