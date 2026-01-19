import { defineConfig } from "@hey-api/openapi-ts"

export default defineConfig({
  input: "./specs/agent.openapi.json",
  output: "./src/client/agent",
})
