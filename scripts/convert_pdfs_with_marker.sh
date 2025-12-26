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
# Environment Variables:
#   MARKER_LLM_API_KEY - API key for LLM services (recommended for LLM providers)
#
# Prerequisites:
#   - marker-pdf installed: pip install marker-pdf
#   - project_pdfs directory exists with PDF files
#   - For LLM services: Set MARKER_LLM_API_KEY environment variable
#
# Output:
#   - Markdown files will be created in project_markdowns directory
#   - Directory structure mirrors project_pdfs
#
# Supported Marker Options:
#   --llm_provider <provider>    LLM provider (openai, anthropic, google, etc.)
#   --llm_model <model>          Specific LLM model to use
#   --langs <language>           Language(s) for OCR (e.g., English, Spanish)
#   --batch_multiplier <num>     Process multiple PDFs in parallel
#   --workers <num>              Number of worker processes
#   And other marker CLI options - pass them after the project name
#

set -e  # Exit on error
set -u  # Exit on undefined variable

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
    
    # Run marker conversion with additional options
    # marker command converts single PDF file
    local output_dir="$(dirname "$markdown_file")"
    local output_basename="$(basename "${markdown_file%.md}")"
    local temp_error_log="/tmp/marker_error_$$.log"
    
    # Build marker command with extra options
    local marker_cmd="marker \"$pdf_path\" \"$output_dir\" --output_format markdown --filename \"$output_basename\""
    
    # Add extra options if provided
    if [ -n "$MARKER_EXTRA_OPTS" ]; then
        marker_cmd="$marker_cmd $MARKER_EXTRA_OPTS"
    fi
    
    # Add API key if available in environment
    if [ -n "${MARKER_LLM_API_KEY:-}" ]; then
        marker_cmd="$marker_cmd --llm_api_key \"$MARKER_LLM_API_KEY\""
    fi
    
    if eval "$marker_cmd" > /dev/null 2>"$temp_error_log"; then
        log_success "Converted: $relative_path → ${relative_path%.pdf}.md"
        rm -f "$temp_error_log"
        return 0
    else
        log_error "Failed to convert: $relative_path"
        if [ -f "$temp_error_log" ]; then
            cat "$temp_error_log" >&2
            rm -f "$temp_error_log"
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
    
    # Show LLM API key status
    if [ -n "${MARKER_LLM_API_KEY:-}" ]; then
        log_info "LLM API key detected (will be passed to Marker)"
    fi
    
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
