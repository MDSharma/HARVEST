/*
  # Create Projects and Papers Tables

  1. New Tables
    - `projects`
      - `id` (uuid, primary key) - Unique project identifier
      - `name` (text, unique, not null) - Project name
      - `description` (text) - Optional project description
      - `created_by` (text, not null) - Email of project creator
      - `created_at` (timestamptz) - When project was created
      - `updated_at` (timestamptz) - Last update timestamp
    
    - `project_papers`
      - `id` (uuid, primary key) - Unique paper identifier
      - `project_id` (uuid, foreign key) - References projects table
      - `doi` (text, not null) - Digital Object Identifier
      - `pdf_path` (text) - Local path to downloaded PDF
      - `title` (text) - Paper title (from CrossRef/Unpaywall)
      - `authors` (text) - Paper authors
      - `year` (text) - Publication year
      - `fetch_status` (text) - Status: 'pending', 'fetching', 'success', 'failed'
      - `error_message` (text) - Error details if fetch failed
      - `created_at` (timestamptz) - When added to project
      - `fetched_at` (timestamptz) - When PDF was successfully downloaded

  2. Security
    - Enable RLS on both tables
    - Authenticated users can view all projects and papers
    - Only admins can create/modify projects and papers (enforced in backend)

  3. Indexes
    - Index on project_id for fast paper lookups
    - Index on doi for deduplication checks
    - Unique constraint on (project_id, doi) to prevent duplicates
*/

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  description text DEFAULT '',
  created_by text NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create project_papers table
CREATE TABLE IF NOT EXISTS project_papers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  doi text NOT NULL,
  pdf_path text,
  title text,
  authors text,
  year text,
  fetch_status text DEFAULT 'pending' CHECK (fetch_status IN ('pending', 'fetching', 'success', 'failed')),
  error_message text,
  created_at timestamptz DEFAULT now(),
  fetched_at timestamptz,
  UNIQUE(project_id, doi)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_project_papers_project_id ON project_papers(project_id);
CREATE INDEX IF NOT EXISTS idx_project_papers_doi ON project_papers(doi);
CREATE INDEX IF NOT EXISTS idx_project_papers_status ON project_papers(fetch_status);

-- Enable RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_papers ENABLE ROW LEVEL SECURITY;

-- RLS Policies: All authenticated users can view
CREATE POLICY "Authenticated users can view projects"
  ON projects FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Authenticated users can view project papers"
  ON project_papers FOR SELECT
  TO authenticated
  USING (true);

-- Note: INSERT/UPDATE/DELETE operations will be restricted to admins in backend logic