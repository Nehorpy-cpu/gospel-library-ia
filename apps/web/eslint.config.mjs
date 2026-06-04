import { FlatCompat } from "@eslint/eslintrc";
import nextVitals from "eslint-config-next/core-web-vitals.js";

const eslintConfig = [
  ...new FlatCompat({ baseDirectory: import.meta.dirname }).config(nextVitals),
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"]
  }
];

export default eslintConfig;
