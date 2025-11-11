/**
 * Error handling example for OctoLLM SDK
 *
 * Demonstrates proper error handling and retry logic.
 */

import {
  OrchestratorClient,
  AuthenticationError,
  ValidationError,
  RateLimitError,
  TimeoutError,
  NotFoundError
} from '../src';

async function main() {
  const client = new OrchestratorClient({
    apiKey: process.env.OCTOLLM_API_KEY || 'invalid-key',
    maxRetries: 3,
    timeout: 10000
  });

  // Example 1: Handle authentication error
  console.log('=== EXAMPLE 1: AUTHENTICATION ERROR ===');
  try {
    await client.submitTask({
      goal: 'Test task',
      budget: { max_tokens: 1000 }
    });
  } catch (error) {
    if (error instanceof AuthenticationError) {
      console.error('Authentication failed. Please check your API key.');
      console.error(`Error code: ${error.errorCode}`);
      console.error(`Request ID: ${error.requestId}`);
    }
  }

  // Example 2: Handle validation error
  console.log('\n=== EXAMPLE 2: VALIDATION ERROR ===');
  try {
    await client.submitTask({
      goal: 'Too short', // Goal too short (min 10 chars)
      budget: { max_tokens: 1000 }
    });
  } catch (error) {
    if (error instanceof ValidationError) {
      console.error('Validation failed:');
      console.error(`Message: ${error.message}`);
      if (error.details) {
        console.error('Details:', error.details);
      }
    }
  }

  // Example 3: Handle rate limit error
  console.log('\n=== EXAMPLE 3: RATE LIMIT ERROR ===');
  const validClient = new OrchestratorClient({
    apiKey: process.env.OCTOLLM_API_KEY || 'your-key'
  });

  try {
    // Simulate rapid requests that might trigger rate limiting
    const promises = Array.from({ length: 100 }, (_, i) =>
      validClient.submitTask({
        goal: `Task ${i}: Analyze security vulnerability`,
        budget: { max_tokens: 1000 }
      })
    );

    await Promise.all(promises);
  } catch (error) {
    if (error instanceof RateLimitError) {
      console.error('Rate limit exceeded!');
      console.error(`Retry after: ${error.retryAfter} seconds`);

      // Wait and retry
      if (error.retryAfter) {
        console.log(`Waiting ${error.retryAfter} seconds before retry...`);
        await new Promise(resolve => setTimeout(resolve, error.retryAfter! * 1000));
        console.log('Retrying now...');
      }
    }
  }

  // Example 4: Handle not found error
  console.log('\n=== EXAMPLE 4: NOT FOUND ERROR ===');
  try {
    await validClient.getTask('task_nonexistent123');
  } catch (error) {
    if (error instanceof NotFoundError) {
      console.error('Task not found:');
      console.error(`Message: ${error.message}`);
      console.error(`Status code: ${error.statusCode}`);
    }
  }

  // Example 5: Handle timeout
  console.log('\n=== EXAMPLE 5: TIMEOUT ERROR ===');
  const slowClient = new OrchestratorClient({
    apiKey: process.env.OCTOLLM_API_KEY || 'your-key',
    timeout: 100 // Very short timeout
  });

  try {
    await slowClient.submitTask({
      goal: 'This will likely timeout',
      budget: { max_tokens: 1000 }
    });
  } catch (error) {
    if (error instanceof TimeoutError) {
      console.error('Request timed out:');
      console.error(`Message: ${error.message}`);
    }
  }

  // Example 6: Generic error handling with logging
  console.log('\n=== EXAMPLE 6: GENERIC ERROR HANDLING ===');
  try {
    await validClient.submitTask({
      goal: 'Analyze code security with detailed analysis',
      budget: { max_tokens: 10000 }
    });
  } catch (error: any) {
    console.error('An error occurred:');
    console.error(`Type: ${error.constructor.name}`);
    console.error(`Message: ${error.message}`);

    if (error.statusCode) {
      console.error(`HTTP Status: ${error.statusCode}`);
    }

    if (error.errorCode) {
      console.error(`Error Code: ${error.errorCode}`);
    }

    if (error.requestId) {
      console.error(`Request ID: ${error.requestId}`);
      console.error('(Use this ID when contacting support)');
    }

    if (error.details) {
      console.error('Additional details:', JSON.stringify(error.details, null, 2));
    }
  }

  console.log('\n=== REQUEST COUNT ===');
  console.log(`Total requests made: ${client.getRequestCount()}`);
}

// Run the example
main().catch(console.error);
