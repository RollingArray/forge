# Python File Header Standard

Every Python source file in FORGE must begin with a consistent module header.

The header should provide enough context for an engineer to quickly understand what the file is and why it exists.

## Standard Format

```python
"""
<Module / File Name>

Author:
-------
<Original Author Name or FORGE Project>

Purpose:
--------
<Short description of why this module exists.>

Responsibilities:
-----------------
- <Responsibility 1>
- <Responsibility 2>
- <Responsibility 3>
"""
```

## **Guidelines**

### **Module / File Name**

Use a clear human-readable name describing the module.

Do not simply repeat the filename unless the filename itself is meaningful.

### **Author**

Preserve the original author where established by Git history.

Use `FORGE Project` when an individual author cannot be established.

Git history remains the source of truth for subsequent contributors.

### **Purpose**

Explain why the module exists.

Keep it concise, normally two to four lines. Avoid implementation details.

### **Responsibilities**

List the major responsibilities owned by the module.

Keep the list short, normally three to six items.

### **What Should NOT Be Included**

Do not add information that Git, project documentation, or the code already provides.

Avoid:

- Created
- Modified
- Version
- Last Updated
- Reviewed By

Do not include implementation details, temporary notes, or personal comments.

## **Architectural Files**

For files representing an important architectural boundary, the Purpose or Responsibilities section should make that boundary clear.

## **Rule**

Every Python file gets a header. Keep it short, meaningful, and focused on purpose and responsibility.

> The header explains what the file is responsible for. The code explains how it does it.