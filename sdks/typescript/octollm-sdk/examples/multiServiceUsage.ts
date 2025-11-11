/**
 * Multi-service usage example for OctoLLM SDK
 *
 * Demonstrates using multiple specialized arms directly.
 */

import {
  PlannerClient,
  CoderClient,
  JudgeClient,
  SafetyClient
} from '../src';

async function main() {
  const apiKey = process.env.OCTOLLM_API_KEY || 'your-api-key-here';

  // Initialize clients for different services
  const planner = new PlannerClient({ apiKey });
  const coder = new CoderClient({ apiKey });
  const judge = new JudgeClient({ apiKey });
  const safety = new SafetyClient({ apiKey });

  try {
    // Step 1: Plan the task
    console.log('=== STEP 1: PLANNING ===');
    const plan = await planner.plan({
      goal: 'Create a secure user authentication system',
      constraints: ['Use bcrypt for password hashing', 'Include rate limiting'],
      budget: { max_tokens: 5000 }
    });

    console.log(`Generated ${plan.subtasks.length} subtasks`);
    console.log(`Estimated cost: $${plan.estimated_cost_usd}`);
    console.log(`Estimated time: ${plan.estimated_time_seconds}s`);

    plan.subtasks.forEach((subtask, idx) => {
      console.log(`  ${idx + 1}. ${subtask.description} (${subtask.assigned_arm})`);
    });

    // Step 2: Generate code
    console.log('\n=== STEP 2: CODE GENERATION ===');
    const codeResult = await coder.code({
      operation: 'generate',
      prompt: 'Create a Python Flask login function with bcrypt password hashing',
      language: 'python',
      context: {
        framework: 'Flask',
        security_requirements: ['bcrypt', 'rate_limiting']
      }
    });

    console.log('Generated code:');
    console.log(codeResult.code);
    console.log(`\nExplanation: ${codeResult.explanation}`);
    console.log(`Confidence: ${codeResult.confidence}`);

    // Step 3: Safety check
    console.log('\n=== STEP 3: SAFETY CHECK ===');
    const safetyResult = await safety.check({
      content: codeResult.code,
      check_pii: true,
      check_harmful: false
    });

    console.log(`Safe: ${safetyResult.safe}`);
    console.log(`PII detected: ${safetyResult.pii_detected}`);

    if (safetyResult.pii_entities && safetyResult.pii_entities.length > 0) {
      console.log('PII entities found:');
      safetyResult.pii_entities.forEach(entity => {
        console.log(`  - ${entity.type}: ${entity.value} (confidence: ${entity.confidence})`);
      });
    }

    // Step 4: Validate output
    console.log('\n=== STEP 4: VALIDATION ===');
    const validationResult = await judge.validate({
      output: codeResult.code,
      criteria: [
        'Uses bcrypt for password hashing',
        'Includes proper error handling',
        'Follows Flask best practices',
        'No hardcoded secrets'
      ]
    });

    console.log(`Validation passed: ${validationResult.passed}`);
    console.log(`Overall confidence: ${validationResult.confidence}`);

    console.log('\nCriteria results:');
    validationResult.criteria_results.forEach(cr => {
      console.log(`  ${cr.passed ? '✓' : '✗'} ${cr.criterion}`);
      console.log(`    ${cr.explanation}`);
    });

    if (validationResult.issues && validationResult.issues.length > 0) {
      console.log('\nIssues found:');
      validationResult.issues.forEach(issue => {
        console.log(`  - ${issue}`);
      });
    }

  } catch (error: any) {
    console.error('Error:', error.message);
    if (error.statusCode) {
      console.error(`Status Code: ${error.statusCode}`);
    }
    if (error.requestId) {
      console.error(`Request ID: ${error.requestId}`);
    }
  }
}

// Run the example
main().catch(console.error);
