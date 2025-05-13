/**
 * Client Example Generator
 * 
 * Generates code examples for API endpoints in multiple languages
 * Part of the Evidence Management System Enhancement.
 */

const fs = require('fs');
const path = require('path');
const Handlebars = require('handlebars');
const prettier = require('prettier');

// Path to OpenAPI spec
const OPENAPI_PATH = path.join(__dirname, '../docs/openapi.json');
// Output directory for client examples
const OUTPUT_DIR = path.join(__dirname, '../docs/examples');

// Template directory
const TEMPLATE_DIR = path.join(__dirname, '../docs/templates');

// Supported languages
const LANGUAGES = [
  {
    id: 'curl',
    name: 'cURL',
    extension: 'sh',
    templateFile: 'curl.hbs'
  },
  {
    id: 'node',
    name: 'Node.js',
    extension: 'js',
    templateFile: 'node.hbs'
  },
  {
    id: 'python',
    name: 'Python',
    extension: 'py',
    templateFile: 'python.hbs'
  },
  {
    id: 'java',
    name: 'Java',
    extension: 'java',
    templateFile: 'java.hbs'
  },
  {
    id: 'csharp',
    name: 'C#',
    extension: 'cs',
    templateFile: 'csharp.hbs'
  }
];

/**
 * Generate client code examples for all API endpoints
 */
function generateClientExamples() {
  // Create output directory if it doesn't exist
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
  
  // Create template directory if it doesn't exist
  if (!fs.existsSync(TEMPLATE_DIR)) {
    fs.mkdirSync(TEMPLATE_DIR, { recursive: true });
    createDefaultTemplates();
  }
  
  // Read OpenAPI spec
  const openApiSpec = JSON.parse(fs.readFileSync(OPENAPI_PATH, 'utf8'));
  
  // Create examples directory structure
  for (const language of LANGUAGES) {
    const langDir = path.join(OUTPUT_DIR, language.id);
    if (!fs.existsSync(langDir)) {
      fs.mkdirSync(langDir, { recursive: true });
    }
  }
  
  // Process each endpoint
  for (const [path, pathItem] of Object.entries(openApiSpec.paths)) {
    for (const [method, operation] of Object.entries(pathItem)) {
      if (['get', 'post', 'put', 'delete', 'patch'].includes(method)) {
        // Generate examples for each language
        generateExamplesForOperation(path, method, operation, openApiSpec);
      }
    }
  }
  
  // Generate index file
  generateIndexFile(openApiSpec);
  
  console.log(`Client examples generated successfully in ${OUTPUT_DIR}`);
  return true;
}

/**
 * Generate examples for a specific operation
 */
function generateExamplesForOperation(path, method, operation, openApiSpec) {
  const operationId = operation.operationId || `${method}${path.replace(/[^a-zA-Z0-9]/g, '')}`;
  
  // Create example data model
  const model = {
    title: operation.summary || `${method.toUpperCase()} ${path}`,
    description: operation.description || '',
    path,
    method: method.toUpperCase(),
    operationId,
    baseUrl: openApiSpec.servers[0].url,
    parameters: operation.parameters || [],
    requestBody: operation.requestBody,
    responses: operation.responses,
    security: operation.security || []
  };
  
  // Generate example for each language
  for (const language of LANGUAGES) {
    // Load template
    const templatePath = path.join(TEMPLATE_DIR, language.templateFile);
    const template = Handlebars.compile(fs.readFileSync(templatePath, 'utf8'));
    
    // Generate code
    const code = template(model);
    
    // Save to file
    const fileName = `${operationId}.${language.extension}`;
    const filePath = path.join(OUTPUT_DIR, language.id, fileName);
    
    fs.writeFileSync(filePath, code);
  }
}

/**
 * Generate index file with links to all examples
 */
function generateIndexFile(openApiSpec) {
  let markdown = '# API Client Examples\n\n';
  
  // Group by tags
  const tagGroups = {};
  
  for (const [path, pathItem] of Object.entries(openApiSpec.paths)) {
    for (const [method, operation] of Object.entries(pathItem)) {
      if (['get', 'post', 'put', 'delete', 'patch'].includes(method)) {
        const tag = (operation.tags && operation.tags[0]) || 'general';
        const operationId = operation.operationId || `${method}${path.replace(/[^a-zA-Z0-9]/g, '')}`;
        
        if (!tagGroups[tag]) {
          tagGroups[tag] = [];
        }
        
        tagGroups[tag].push({
          path,
          method,
          operationId,
          summary: operation.summary || `${method.toUpperCase()} ${path}`
        });
      }
    }
  }
  
  // Generate markdown for each tag
  for (const [tag, operations] of Object.entries(tagGroups)) {
    markdown += `## ${tag}\n\n`;
    
    for (const operation of operations) {
      markdown += `### ${operation.summary}\n\n`;
      markdown += `${operation.method.toUpperCase()} ${operation.path}\n\n`;
      
      markdown += 'Available in:\n\n';
      
      for (const language of LANGUAGES) {
        markdown += `- [${language.name}](${language.id}/${operation.operationId}.${language.extension})\n`;
      }
      
      markdown += '\n';
    }
  }
  
  fs.writeFileSync(path.join(OUTPUT_DIR, 'README.md'), markdown);
}

/**
 * Create default templates if they don't exist
 */
function createDefaultTemplates() {
  const templates = {
    'curl.hbs': `# {{title}}
# {{description}}

curl -X {{method}} "{{baseUrl}}{{path}}"{{#if parameters}} \\
{{#each parameters}}  -d "{{name}}=value"{{#unless @last}} \\{{/unless}}
{{/each}}{{/if}}{{#if requestBody}} \\
  -H "Content-Type: application/json" \\
  -d '{
  {{#each requestBody.content.[application/json].schema.properties}}
    "{{@key}}": "value"{{#unless @last}},{{/unless}}
  {{/each}}
  }'{{/if}}{{#if security}} \\
  -H "X-API-Key: YOUR_API_KEY"{{/if}}`,
  
    'node.hbs': `/**
 * {{title}}
 * {{description}}
 */
const axios = require('axios');

async function {{operationId}}() {
  try {
    {{#if requestBody}}
    const requestBody = {
      {{#each requestBody.content.[application/json].schema.properties}}
      {{@key}}: "value",
      {{/each}}
    };
    {{/if}}
    
    const response = await axios({
      method: '{{method}}',
      url: '{{baseUrl}}{{path}}',
      {{#if parameters}}
      params: {
        {{#each parameters}}
        {{#if (eq in "query")}}
        {{name}}: "value",
        {{/if}}
        {{/each}}
      },
      {{/if}}
      {{#if requestBody}}
      data: requestBody,
      {{/if}}
      {{#if security}}
      headers: {
        'X-API-Key': 'YOUR_API_KEY'
      }
      {{/if}}
    });
    
    console.log('Success:', response.data);
    return response.data;
  } catch (error) {
    console.error('Error:', error.response ? error.response.data : error.message);
    throw error;
  }
}

// Example usage
{{operationId}}().catch(console.error);`,
  
    'python.hbs': `"""
{{title}}
{{description}}
"""
import requests

def {{operationId}}():
    {{#if requestBody}}
    request_body = {
        {{#each requestBody.content.[application/json].schema.properties}}
        "{{@key}}": "value",
        {{/each}}
    }
    {{/if}}
    
    {{#if security}}
    headers = {
        "X-API-Key": "YOUR_API_KEY"
    }
    {{else}}
    headers = {}
    {{/if}}
    
    {{#if parameters}}
    params = {
        {{#each parameters}}
        {{#if (eq in "query")}}
        "{{name}}": "value",
        {{/if}}
        {{/each}}
    }
    {{else}}
    params = {}
    {{/if}}
    
    try:
        response = requests.{{method}}(
            "{{baseUrl}}{{path}}",
            {{#if requestBody}}
            json=request_body,
            {{/if}}
            headers=headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        print(f"Response: {err.response.text}")
        raise
    except Exception as err:
        print(f"Error: {err}")
        raise

# Example usage
if __name__ == "__main__":
    result = {{operationId}}()
    print(result)`,
  
    'java.hbs': `import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpRequest.BodyPublishers;
import java.net.http.HttpResponse.BodyHandlers;

/**
 * {{title}}
 * {{description}}
 */
public class {{operationId}} {
    public static void main(String[] args) {
        try {
            {{operationId}}Example();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    
    public static void {{operationId}}Example() throws Exception {
        HttpClient client = HttpClient.newHttpClient();
        
        {{#if requestBody}}
        String requestBody = """
            {
            {{#each requestBody.content.[application/json].schema.properties}}
                "{{@key}}": "value"{{#unless @last}},{{/unless}}
            {{/each}}
            }
            """;
        {{/if}}
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("{{baseUrl}}{{path}}"))
            .method("{{method}}", {{#if requestBody}}BodyPublishers.ofString(requestBody){{else}}BodyPublishers.noBody(){{/if}})
            {{#if security}}
            .header("X-API-Key", "YOUR_API_KEY")
            {{/if}}
            {{#if requestBody}}
            .header("Content-Type", "application/json")
            {{/if}}
            .build();
            
        HttpResponse<String> response = client.send(request, BodyHandlers.ofString());
        
        System.out.println("Status code: " + response.statusCode());
        System.out.println("Response: " + response.body());
    }
}`,
  
    'csharp.hbs': `using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Text.Json;

/// <summary>
/// {{title}}
/// {{description}}
/// </summary>
public class {{operationId}}Example
{
    static readonly HttpClient client = new HttpClient();
    
    static async Task Main()
    {
        try
        {
            await {{operationId}}();
        }
        catch (Exception e)
        {
            Console.WriteLine($"Exception: {e.Message}");
        }
    }
    
    static async Task {{operationId}}()
    {
        {{#if security}}
        client.DefaultRequestHeaders.Add("X-API-Key", "YOUR_API_KEY");
        {{/if}}
        
        {{#if requestBody}}
        var requestData = new {
            {{#each requestBody.content.[application/json].schema.properties}}
            {{@key}} = "value",
            {{/each}}
        };
        
        var json = JsonSerializer.Serialize(requestData);
        var content = new StringContent(json, Encoding.UTF8, "application/json");
        {{/if}}
        
        var response = await client.{{method}}Async(
            "{{baseUrl}}{{path}}"{{#if requestBody}},
            content{{/if}}
        );
        
        response.EnsureSuccessStatusCode();
        
        var responseBody = await response.Content.ReadAsStringAsync();
        Console.WriteLine(responseBody);
    }
}`
  };
  
  // Write default templates
  for (const [fileName, content] of Object.entries(templates)) {
    fs.writeFileSync(path.join(TEMPLATE_DIR, fileName), content);
  }
}

// Add Handlebars helpers
Handlebars.registerHelper('eq', function(a, b) {
  return a === b;
});

// Execute if this script is run directly
if (require.main === module) {
  generateClientExamples();
}

// Export for use in other scripts
module.exports = {
  generateClientExamples
};
