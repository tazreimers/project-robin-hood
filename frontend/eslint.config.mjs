import path from "node:path";
import { fileURLToPath } from "node:url";

import { FlatCompat } from "@eslint/eslintrc";
import js from "@eslint/js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({
  baseDirectory: __dirname,
  recommendedConfig: js.configs.recommended,
  allConfig: js.configs.all,
});

export default [
  {
    ignores: [
      "node_modules/",
      "**/node_modules/",
      ".next/",
      "out/",
      "build/",
      "coverage/",
      "dist/",
      "*.config.*",
      ".prettierrc.cjs",
      "eslint.config.mjs",
      "next-env.d.ts",
      "**/*.d.ts",
      "**/*.d.tsx",
      "**/*.test.ts",
      "**/*.test.tsx",
      "**/*.md",
      "**/*.css",
      "package-lock.json",
    ],
  },
  ...compat.config({
    extends: [
      "eslint:recommended",
      "next/core-web-vitals",
      "plugin:@typescript-eslint/recommended-requiring-type-checking",
      "plugin:@typescript-eslint/recommended",
      "plugin:react/recommended",
    ],
    env: {
      browser: true,
      es2022: true,
      node: true,
    },
    rules: {
      eqeqeq: ["warn", "smart"],
      "@typescript-eslint/ban-ts-comment": "warn",
      "@typescript-eslint/consistent-type-exports": "warn",
      "@typescript-eslint/no-empty-function": "off",
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-for-in-array": "warn",
      "@typescript-eslint/no-unused-expressions": "warn",
      "@typescript-eslint/no-misused-promises": [
        "error",
        {
          checksVoidReturn: {
            attributes: false,
          },
        },
      ],
      "@typescript-eslint/no-non-null-assertion": "warn",
      "@typescript-eslint/no-unnecessary-type-assertion": "warn",
      "@typescript-eslint/no-unsafe-argument": "warn",
      "@typescript-eslint/no-unsafe-assignment": "warn",
      "@typescript-eslint/no-unsafe-call": "warn",
      "@typescript-eslint/no-unsafe-member-access": "warn",
      "@typescript-eslint/no-unsafe-return": "warn",
      "@typescript-eslint/require-await": "warn",
      "@typescript-eslint/restrict-plus-operands": "warn",
      "@typescript-eslint/restrict-template-expressions": "warn",
      "@typescript-eslint/unbound-method": "warn",
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          caughtErrors: "all",
          caughtErrorsIgnorePattern: "^_",
          ignoreRestSiblings: true,
        },
      ],
      "@typescript-eslint/no-inferrable-types": "off",
      "@typescript-eslint/no-base-to-string": "warn",
      "@typescript-eslint/no-empty-object-type": "warn",
      "@typescript-eslint/no-redundant-type-constituents": "warn",
      "@typescript-eslint/no-duplicate-type-constituents": "warn",
      "@typescript-eslint/no-unsafe-enum-comparison": "warn",
      "@typescript-eslint/only-throw-error": "warn",
      "@typescript-eslint/prefer-promise-reject-errors": "warn",
      "jsx-a11y/alt-text": "off",
      "no-async-promise-executor": "warn",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-empty": "off",
      "no-extra-boolean-cast": "warn",
      "no-type-assertion/no-type-assertion": "warn",
      "react-hooks/exhaustive-deps": "warn",
      "react-hooks/rules-of-hooks": "error",
      "react/display-name": "warn",
      "react/no-children-prop": "off",
      "react/prop-types": "off",
      "react/react-in-jsx-scope": "off",
      curly: ["error", "all"],
      "no-unsafe-optional-chaining": "warn",
    },
    settings: {
      next: {
        rootDir: ".",
      },
      react: {
        version: "18.3",
      },
    },
    parser: "@typescript-eslint/parser",
    parserOptions: {
      project: "./tsconfig.json",
      tsconfigRootDir: __dirname,
    },
    plugins: ["@typescript-eslint", "no-type-assertion", "react-hooks", "react"],
  }),
];
