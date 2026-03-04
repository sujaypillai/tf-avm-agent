---
description: Convert an architecture diagram into Terraform code using Azure Verified Modules
mode: terraform-expert
---

# Analyze Architecture Diagram

You are converting a visual architecture diagram into a production-ready Terraform project.

## Input

Provide an architecture diagram image showing Azure services and their relationships.

## Steps

1. **Identify services**: Examine the diagram to identify all Azure services depicted (look for service icons, labels, and connection lines)
2. **Map relationships**: Determine how services are connected — which depend on which, network topology, data flows
3. **List Azure services**: Create a structured list of identified services with their roles
4. **Map to AVM modules**: Find the matching Azure Verified Module for each service
5. **Resolve dependencies**: Build a dependency graph based on the diagram relationships
6. **Generate Terraform**: Create the complete project following AVM best practices

## Tips for Diagram Analysis

- Look for Azure service icons (blue icons with service-specific shapes)
- Identify network boundaries (VNets, subnets, NSGs)
- Note data flow directions (arrows between services)
- Check for managed identities, private endpoints, and security features
- Look for monitoring/logging services (Log Analytics, Application Insights)

## Output

A complete Terraform project with all identified services, properly wired dependencies, and AVM best practices applied.
