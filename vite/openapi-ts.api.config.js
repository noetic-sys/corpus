import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./specs/api.openapi.json",
  output: "./src/client/api",
})
