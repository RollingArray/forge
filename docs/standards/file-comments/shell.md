# Shell Script Header Standard

Every shell script in FORGE must begin with a consistent file header immediately after its shebang.

## Standard Format

```bash
#!/usr/bin/env bash
#
# <Script Name>
#
# Author:
# -------
# Ranjoy Sen
#
# Purpose:
# --------
# <Short description of why this script exists.>
#
# Responsibilities:
# -----------------
# - <Responsibility 1>
# - <Responsibility 2>
# - <Responsibility 3>
````

## **Guidelines**

### **Script Name**

Use a clear human-readable name describing the script.

### **Author**

Use `Ranjoy Sen` as the author attribution.

### **Purpose**

Explain why the script exists. Keep it concise and avoid implementation details.

### **Responsibilities**

List the major operations performed by the script. Normally use three to six items.

Mention important side effects, such as creating or removing deployment artifacts, starting or stopping services, or preserving runtime data.

### **Usage**

Include invocation instructions when the script requires arguments or has a meaningful execution mode.

### **What Should NOT Be Included**

Avoid Created, Modified, Version, Last Updated, and Reviewed By.

Do not include temporary notes or implementation details.

## **Rule**

Every shell script gets a header immediately after its shebang. Keep it short, meaningful, and focused on purpose and responsibility.

> The header explains what the script is responsible for. The commands explain how it does it.