/**
 * JSDoc to OpenAPI Converter
 * 
 * Parses JSDoc comments from Express routes and generates OpenAPI documentation.
 * Part of the Evidence Management System Enhancement.
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');
const doctrine = require('doctrine');
const swaggerJSDoc = require('swagger-jsdoc');
const prettier = require('prettier');

// Configuration - adjust these paths as needed
const SRC_ROUTES_PATTERN = path.join(__dirname, '../routes/**/*.js');
const OPENAPI_OUTPUT_PATH = path.join(__dirname, '../docs/openapi.json');

// Base OpenAPI document - this will be extended with JSDoc annotations
const baseOpenApiDocument = {
  openapi: '3.0.0',
  info: {
    title: 'Evidence Management System API',
    description: 'API for managing evidence in the Real Senti CLI Kanban project',
    version: '1.0.0',
    contact: {
      email: 'support@realsenti.com'
    }
  },
  servers: [
    {
      url: 'http://localhost:3000',
      description: 'Local development server'
    }
  ],
  tags: [
    {
      name: 'evidence',
      description: 'Evidence operations'
    },
    {
      name: 'attachments',
      description: 'Evidence attachment operations'
    },
    {
      name: 'batch',
      description: 'Batch operations for evidence management'
    },
    {
      name: 'webhooks',
      description: 'Webhook configuration and events'
    }
  ]
};

// Swagger JSDoc options
const options = {
  definition: baseOpenApiDocument,
  apis: [SRC_ROUTES_PATTERN]
};

/**
 * Generate OpenAPI documentation from JSDoc comments
 */
function generateOpenApiDocs() {
  console.log('Generating OpenAPI documentation from JSDoc comments...');
  
  try {
    // Generate OpenAPI spec from JSDoc annotations
    const openapiSpec = swaggerJSDoc(options);
    
    // Format the JSON for better readability
    const formattedJson = prettier.format(JSON.stringify(openapiSpec), {
      parser: 'json',
      tabWidth: 2
    });
    
    // Write the OpenAPI spec to file
    fs.writeFileSync(OPENAPI_OUTPUT_PATH, formattedJson);
    
    console.log(`OpenAPI documentation successfully generated at ${OPENAPI_OUTPUT_PATH}`);
    return true;
  } catch (error) {
    console.error('Error generating OpenAPI documentation:', error);
    return false;
  }
}

/**
 * Extract route information from Express app
 * This is useful for validating that all routes have JSDoc comments
 */
function extractRoutes(app) {
  const routes = [];
  
  function processStack(stack, basePath = '') {
    stack.forEach(layer => {
      if (layer.route) {
        // This is a route
        const methods = Object.keys(layer.route.methods)
          .filter(method => layer.route.methods[method])
          .map(method => method.toUpperCase());
        
        routes.push({
          path: basePath + layer.route.path,
          methods
        });
      } else if (layer.name === 'router' && layer.handle.stack) {
        // This is a router
        const newBasePath = basePath + (layer.regexp.source.replace(/\\\\\\\/\?\(\?\=\\\\\\\/$\|$\)/, '').replace(/^\^\\\\\\\//, '/').replace(/\\\\\\\//g, '/') || '');
        processStack(layer.handle.stack, newBasePath);
      }
    });
  }
  
  if (app._router && app._router.stack) {
    processStack(app._router.stack);
  }
  
  return routes;
}

/**
 * Check if all routes have JSDoc comments
 * Useful for detecting missing documentation
 */
function checkRoutesDocumentation(app) {
  const routes = extractRoutes(app);
  const openApiSpec = JSON.parse(fs.readFileSync(OPENAPI_OUTPUT_PATH, 'utf8'));
  
  const missingDocs = [];
  
  routes.forEach(route => {
    // Skip non-API routes
    if (!route.path.startsWith('/api/')) {
      return;
    }
    
    // Check if route exists in OpenAPI spec
    const pathExists = Object.keys(openApiSpec.paths || {}).some(specPath => {
      // Normalize path parameters for comparison
      const normalizedSpecPath = specPath.replace(/{[^}]+}/g, '{param}');
      const normalizedRoutePath = route.path.replace(/:[^/]+/g, '{param}');
      return normalizedSpecPath === normalizedRoutePath;
    });
    
    if (!pathExists) {
      missingDocs.push(route);
    }
  });
  
  return missingDocs;
}

// Execute if this script is run directly
if (require.main === module) {
  generateOpenApiDocs();
}

// Export for use in other scripts
module.exports = {
  generateOpenApiDocs,
  extractRoutes,
  checkRoutesDocumentation
};
