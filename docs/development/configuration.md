# FORGE Configuration

## Configuration Files

FORGE uses configuration files for application-specific settings.

The configuration files identified in the project README are:

  File                              Purpose
  --------------------------------- -----------------------------
  `backend/api/config/ai.json`      AI-related configuration
  `backend/api/config/email.json`   Email-related configuration

Keep these files aligned with the configuration expected by the
application.

## Sensitive Configuration

Do not commit secrets, credentials, tokens, or other sensitive values to
the repository.

Before sharing configuration files or including them in deployment
artifacts, check that they do not contain credentials or other sensitive
information.

Use the configuration structure expected by the application. Do not add
new keys or assume environment-variable names without confirming that
the application supports them.

## Configuration Changes

When changing configuration:

1.  Check the relevant application code to understand which settings are
    read.
2.  Preserve the expected JSON structure and key names.
3.  Avoid placing secrets in source control.
4.  Verify the affected application behavior after making the change.

## Related Documentation

-   [Environment Setup](environment-setup.md)
-   [Local Development](local-development.md)
-   [Deployment and Script
    Guide](../deployment/deployment-and-script-guide.md)
