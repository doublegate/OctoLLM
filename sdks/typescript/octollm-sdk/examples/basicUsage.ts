/**
 * Basic usage example for OctoLLM SDK
 *
 * Demonstrates submitting a task and polling for completion.
 */

import { OrchestratorClient, TaskRequest } from '../src';

async function main() {
  // Initialize client with API key
  const client = new OrchestratorClient({
    baseUrl: 'http://localhost:8000',
    apiKey: process.env.OCTOLLM_API_KEY || 'your-api-key-here',
    timeout: 30000
  });

  // Create a task request
  const taskRequest: TaskRequest = {
    goal: 'Analyze the security vulnerabilities in the provided Python web application',
    constraints: [
      'Focus on OWASP Top 10 vulnerabilities',
      'Include SQL injection and XSS analysis'
    ],
    acceptance_criteria: [
      'All high-severity vulnerabilities identified',
      'Remediation recommendations provided',
      'Code examples for fixes included'
    ],
    context: {
      framework: 'Flask',
      python_version: '3.11',
      authentication: 'JWT'
    },
    budget: {
      max_tokens: 10000,
      max_time_seconds: 120,
      max_cost_dollars: 1.0
    }
  };

  try {
    // Submit task
    console.log('Submitting task...');
    const response = await client.submitTask(taskRequest);
    console.log(`Task submitted: ${response.task_id}`);
    console.log(`Status: ${response.status}`);
    console.log(`Created at: ${response.created_at}`);

    // Poll for completion
    console.log('\nPolling for completion...');
    let attempts = 0;
    const maxAttempts = 60; // 2 minutes with 2-second intervals

    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds

      const status = await client.getTask(response.task_id);
      console.log(`Status: ${status.status}`);

      if (status.progress) {
        console.log(
          `Progress: ${status.progress.percentage}% ` +
          `(${status.progress.current_step})`
        );
      }

      // Check if task is complete
      if (['completed', 'failed', 'cancelled'].includes(status.status)) {
        console.log('\nTask finished!');

        if (status.status === 'completed' && status.result) {
          console.log('\n=== RESULT ===');
          console.log(`Output: ${status.result.output}`);
          console.log(`Confidence: ${status.result.confidence}`);
          console.log(`Validation Passed: ${status.result.validation_passed}`);
        } else if (status.status === 'failed' && status.error) {
          console.log('\n=== ERROR ===');
          console.log(`Type: ${status.error.type}`);
          console.log(`Message: ${status.error.message}`);
          if (status.error.details) {
            console.log(`Details: ${status.error.details}`);
          }
        }

        break;
      }

      attempts++;
    }

    if (attempts >= maxAttempts) {
      console.log('\nTimeout: Task did not complete in time');
    }

  } catch (error: any) {
    console.error('Error:', error.message);
    if (error.statusCode) {
      console.error(`Status Code: ${error.statusCode}`);
    }
    if (error.details) {
      console.error('Details:', error.details);
    }
  }
}

// Run the example
main().catch(console.error);
