export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { assertDeploymentConfiguration } = await import("./lib/deployment-config");
    assertDeploymentConfiguration();
  }
}
