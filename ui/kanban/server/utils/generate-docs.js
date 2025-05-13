/**
 * Documentation Generator
 * 
 * Coordinates the generation of comprehensive API documentation.
 * Part of the Evidence Management System Enhancement.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Import documentation utilities
const { generateOpenApiDocs } = require('./jsdoc2openapi');
const { generateClientExamples } = require('./generate-client-examples');

// Path to package.json to update scripts
const PACKAGE_JSON_PATH = path.join(__dirname, '../../package.json');

// Documentation output directory
const DOCS_DIR = path.join(__dirname, '../docs');

/**
 * Generate all documentation components
 */
function generateAllDocs() {
  console.log('Starting comprehensive documentation generation...');
  
  // Ensure docs directory exists
  if (!fs.existsSync(DOCS_DIR)) {
    fs.mkdirSync(DOCS_DIR, { recursive: true });
  }
  
  // Step 1: Generate OpenAPI docs from JSDoc comments
  console.log('\n1. Generating OpenAPI documentation from JSDoc comments...');
  const openApiResult = generateOpenApiDocs();
  
  if (!openApiResult) {
    console.error('Failed to generate OpenAPI documentation. Aborting.');
    return false;
  }
  
  // Step 2: Generate client examples from OpenAPI spec
  console.log('\n2. Generating client examples in multiple languages...');
  const clientExamplesResult = generateClientExamples();
  
  if (!clientExamplesResult) {
    console.warn('Warning: Failed to generate client examples.');
  }
  
  // Step 3: Copy static documentation files
  console.log('\n3. Setting up static documentation files...');
  ensureStaticDocsExist();
  
  // Step 4: Update package.json with documentation scripts
  console.log('\n4. Adding documentation scripts to package.json...');
  updatePackageJsonScripts();
  
  // Step 5: Generate main documentation page
  console.log('\n5. Generating main documentation page...');
  generateMainDocPage();
  
  console.log('\nDocumentation generation complete!');
  console.log(`View the documentation at: ${path.join(DOCS_DIR, 'index.html')}`);
  
  return true;
}

/**
 * Ensure all static documentation files exist
 */
function ensureStaticDocsExist() {
  // List of static docs files that should be present
  const staticDocs = [
    'error-documentation.md',
    'auth-guide.md'
  ];
  
  let allExist = true;
  
  for (const doc of staticDocs) {
    const docPath = path.join(DOCS_DIR, doc);
    if (!fs.existsSync(docPath)) {
      console.error(`Missing static documentation file: ${doc}`);
      allExist = false;
    }
  }
  
  return allExist;
}

/**
 * Update package.json with documentation scripts
 */
function updatePackageJsonScripts() {
  try {
    const packageJson = JSON.parse(fs.readFileSync(PACKAGE_JSON_PATH, 'utf8'));
    
    // Add documentation scripts
    packageJson.scripts = packageJson.scripts || {};
    
    // Add/update documentation scripts
    const scripts = {
      'docs:generate': 'node server/utils/generate-docs.js',
      'docs:serve': 'npx serve server/docs',
      'docs:api': 'node server/utils/jsdoc2openapi.js',
      'docs:examples': 'node server/utils/generate-client-examples.js',
      'docs:dev': 'npm run docs:generate && npm run docs:serve'
    };
    
    let scriptCount = 0;
    
    for (const [key, value] of Object.entries(scripts)) {
      if (!packageJson.scripts[key] || packageJson.scripts[key] !== value) {
        packageJson.scripts[key] = value;
        scriptCount++;
      }
    }
    
    if (scriptCount > 0) {
      fs.writeFileSync(PACKAGE_JSON_PATH, JSON.stringify(packageJson, null, 2));
      console.log(`Added/updated ${scriptCount} documentation scripts in package.json`);
    } else {
      console.log('Documentation scripts already up to date in package.json');
    }
    
    return true;
  } catch (error) {
    console.error('Error updating package.json:', error);
    return false;
  }
}

/**
 * Generate the main documentation page
 */
function generateMainDocPage() {
  const mainPageContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Evidence Management System - Documentation</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      padding-top: 2rem;
      padding-bottom: 2rem;
    }
    .nav-link.active {
      font-weight: bold;
    }
    .jumbotron {
      padding: 2rem;
      background-color: #f8f9fa;
      border-radius: 0.3rem;
      margin-bottom: 2rem;
    }
    .card {
      margin-bottom: 1.5rem;
      transition: transform 0.2s;
    }
    .card:hover {
      transform: translateY(-5px);
      box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .footer {
      margin-top: 3rem;
      padding: 1.5rem 0;
      color: #6c757d;
      border-top: 1px solid #e9ecef;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="jumbotron">
      <h1 class="display-4">Evidence Management System</h1>
      <p class="lead">Comprehensive API documentation for the Evidence Management System</p>
      <hr class="my-4">
      <p>Use the links below to explore the API documentation, view examples, and learn about error handling and authentication.</p>
    </div>
    
    <div class="row">
      <div class="col-md-4">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">API Reference</h5>
            <p class="card-text">Interactive API documentation with all endpoints, parameters, and responses.</p>
            <a href="./index.html" class="btn btn-primary">View API Reference</a>
          </div>
        </div>
      </div>
      
      <div class="col-md-4">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">Client Examples</h5>
            <p class="card-text">Code examples for API integration in multiple programming languages.</p>
            <a href="./examples/README.md" class="btn btn-primary">View Examples</a>
          </div>
        </div>
      </div>
      
      <div class="col-md-4">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">Error Documentation</h5>
            <p class="card-text">Detailed information on API errors and how to handle them.</p>
            <a href="./error-documentation.md" class="btn btn-primary">View Error Docs</a>
          </div>
        </div>
      </div>
    </div>
    
    <div class="row mt-4">
      <div class="col-md-6">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">Authentication Guide</h5>
            <p class="card-text">Learn how to authenticate with the API and understand permissions.</p>
            <a href="./auth-guide.md" class="btn btn-primary">View Auth Guide</a>
          </div>
        </div>
      </div>
      
      <div class="col-md-6">
        <div class="card">
          <div class="card-body">
            <h5 class="card-title">Command Line Interface</h5>
            <p class="card-text">Documentation for the Kanban CLI commands for evidence management.</p>
            <a href="../../README.md" class="btn btn-primary">View CLI Docs</a>
          </div>
        </div>
      </div>
    </div>
    
    <div class="footer text-center">
      <p>Evidence Management System – API Documentation – Generated: ${new Date().toLocaleDateString()}</p>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>`;

  fs.writeFileSync(path.join(DOCS_DIR, 'documentation.html'), mainPageContent);
  return true;
}

// Execute if this script is run directly
if (require.main === module) {
  generateAllDocs();
}

// Export for use in other scripts
module.exports = {
  generateAllDocs
};
