# Test Automation Code Generator Prompt

You are an expert test automation engineer. Your task is to generate Playwright test code with TypeScript for the following test case using Cucumber format and the Page Object Model.

---

## Test Case Details
- **Test Case Name**: {test_case_name}
- **Description**: {description}
- **Framework**: {framework}
- **Language**: {language}

---

## Steps
```gherkin
{steps}
```

## UI ↔ API Mapping
```json
{mapping_json}
```

## CDP Recording
{cdp_section}

## Additional Instructions


---

## Requirements
Please generate test code that:
1. Uses Playwright's best practices and TypeScript features
2. Implements the Page Object Model pattern
3. Handles network interception and mocking when needed
4. Includes proper error handling and assertions (use retry pattern for flaky actions)
5. Handles async operations correctly
6. Uses Cucumber with Playwright for BDD
7. Implements proper logging and reporting (add logging in step definitions and helpers)
8. Uses appropriate selectors and waiting strategies (see Selectors Priority below)
9. Includes proper documentation and JSDoc comments
10. Follows parameter naming that matches Gherkin steps or test data keys

---

## Output Formatting Rules

- **Always output each file in a separate TypeScript or feature code block.**
- **At the top of each code block, include a comment with the file path (e.g., `// tests/pages/login.page.ts`).**
- **Do not include explanations or extra commentary—output only the code/files as specified.**
- **If multiple scenarios are provided, generate all of them in the same feature file.**
- **If YAML or custom instructions are provided, always prioritize them for step logic, data, or API handling.**

---

## Common Patterns to Follow

### 1. Page Object Pattern
```typescript
// Page Object Interface
interface LoginPageInterface {
    username: Locator;
    password: Locator;
    loginButton: Locator;
    login(username: string, password: string): Promise<void>;
}

// Page Object Implementation
class LoginPage implements LoginPageInterface {
    readonly page: Page;
    readonly username: Locator;
    readonly password: Locator;
    readonly loginButton: Locator;

    constructor(page: Page) {
        this.page = page;
        this.username = page.getByTestId('username-input');
        this.password = page.getByTestId('password-input');
        this.loginButton = page.getByRole('button', { name: 'Login' });
    }

    async login(username: string, password: string): Promise<void> {
        await this.username.fill(username);
        await this.password.fill(password);
        await this.loginButton.click();
        await this.page.waitForURL('**/dashboard');
    }
}
```

### 2. Test Data Pattern
```typescript
import fs from 'fs';
import path from 'path';

export function loadTestData<T>(fileName: string): T {
    const dataPath = path.join(process.cwd(), 'test-data', fileName);
    const rawData = fs.readFileSync(dataPath, 'utf8');
    return JSON.parse(rawData) as T;
}

Given('I am logged in as {string} user', async function(userType: string) {
    const users = loadTestData<Record<string, UserData>>('users.json');
    const user = users[userType];
    const loginPage = new LoginPage(this.page);
    await loginPage.login(user.username, user.password);
});
```

### 3. Cucumber Step Definitions
```typescript
import { Given, When, Then } from '@cucumber/cucumber';
import { expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { loadTestData } from '../helpers/file-loader';

Given('I am on the login page', async function() {
    await this.page.goto('/login');
});

When('I enter {string} credentials', async function(userType: string) {
    const users = loadTestData('users.json');
    const user = users[userType];
    const loginPage = new LoginPage(this.page);
    await loginPage.username.fill(user.username);
    await loginPage.password.fill(user.password);
});

When('I click the login button', async function() {
    const loginPage = new LoginPage(this.page);
    await loginPage.loginButton.click();
});

Then('I should be redirected to the dashboard', async function() {
    await expect(this.page).toHaveURL(/.*dashboard/);
});

Then('I should see an error message {string}', async function(errorMessage: string) {
    await expect(this.page.getByRole('alert')).toContainText(errorMessage);
});
```

### 4. API Interception and Mocking Patterns
```typescript
// Single API Interception
When('I submit the form with valid data', async function() {
    await this.page.route('**/api/submit', async route => {
        const response = await route.fetch();
        this.apiResponses = this.apiResponses || {};
        this.apiResponses['submit'] = await response.json();
        console.log('Intercepted response:', this.apiResponses['submit']);
        await route.continue();
    });
    await this.page.getByTestId('submit-button').click();
});

// Multiple API Interception in Hooks
Before(async function() {
    this.apiResponses = {};
    const endpoints = [
        '**/api/users',
        '**/api/products',
        '**/api/orders'
    ];
    for (const endpoint of endpoints) {
        await this.page.route(endpoint, async route => {
            const response = await route.fetch();
            const endpointKey = endpoint.replace(/\*\*\/api\//, '');
            this.apiResponses[endpointKey] = await response.json();
            await route.continue();
        });
    }
});
```

### 5. Response Storage and Retrieval
```typescript
Before(async function() {
    this.storedResponses = {};
    this.storeResponse = (key, data) => {
        this.storedResponses[key] = data;
    };
    this.getResponse = (key) => {
        if (!this.storedResponses[key]) {
            throw new Error(`No response stored with key: ${key}`);
        }
        return this.storedResponses[key];
    };
});
```

### 6. UI-API Validation Patterns
```typescript
Then('the user profile should match the API data', async function() {
    const apiResponse = this.getResponse('userProfile');
    await expect(this.page.getByTestId('user-name')).toHaveText(apiResponse.name);
    await expect(this.page.getByTestId('user-email')).toHaveText(apiResponse.email);
    await expect(this.page.getByTestId('user-role')).toHaveText(apiResponse.role);
});
```

### 7. Selectors Priority
1. data-testid: `page.getByTestId('login-button')`
2. Role: `page.getByRole('button', { name: 'Login' })`
3. Label: `page.getByLabel('Username')`
4. Text: `page.getByText('Welcome')`
5. Placeholder: `page.getByPlaceholder('Enter username')`
6. ID/Name: `page.locator('#username')`, `page.locator('[name="username"]')`
- If `data-testid` is not available, fall back to the next selector in the list.

### 8. Error Handling Patterns
```typescript
async function retryOperation(action: () => Promise<void>, maxAttempts = 3): Promise<void> {
    let lastError: Error | null = null;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            await action();
            return;
        } catch (error) {
            lastError = error as Error;
            if (attempt === maxAttempts) throw error;
            await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
    }
}
```

---

## Processing Guidelines


### Code Example Analysis
- Follow existing naming conventions and patterns.
- Reuse selector strategies for consistency.
- Maintain the same error handling approach.
- Follow established project structure.

---

## Output Format

Your output should include the following files based on the test requirements:

### 1. Feature File
- Path: `tests/features/{feature-name}.feature`
- Contains the Gherkin scenario(s) for the test case
- Should follow BDD best practices with clear Given/When/Then statements

### 2. Step Definition File
- Path: `tests/step-definitions/{feature-name}.steps.ts`
- Implements the steps from the feature file
- Uses patterns from the sections above

### 3. Page Object File(s)
- Path: `tests/pages/{page-name}.page.ts`
- Implements the Page Object Model as shown above
- Contains all locators and page-specific methods

### 4. Helper Files (if needed)
- Path: `tests/helpers/file-loader.ts`
- Implements utility functions for loading test data and mocks

### 5. Test Data Files
- Path: `tests/test-data/{entity}.json`
- Contains test data in JSON format

### 6. Mock Response Files (if needed)
- Path: `tests/mocks/{endpoint-name}.json`
- Contains mock API responses in JSON format

---

## Project Structure
```
└── tests/
    ├── features/              # Cucumber feature files
    ├── step-definitions/      # Step implementation files
    ├── pages/                 # Page object classes
    ├── helpers/               # Utility functions and helpers
    ├── test-data/             # JSON test data files
    └── mocks/                 # JSON API mock responses
```

---

**Remember:**  
- Generate code that follows best practices, with an emphasis on readability, maintainability, and consistent patterns throughout all the components.
- Output only the code/files as specified, with file path comments at the top of each code block.
- If YAML or custom instructions are provided, always prioritize them for step logic, data, or API handling.
