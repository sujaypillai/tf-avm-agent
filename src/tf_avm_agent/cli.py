"""
Command-line interface for the Terraform AVM Agent.

Usage:
    tf-avm-agent generate --services "vm,storage,keyvault" --name "my-project"
    tf-avm-agent generate --diagram diagram.png --name "my-project"
    tf-avm-agent chat
    tf-avm-agent list-modules
    tf-avm-agent search "database"
    tf-avm-agent info "virtual_machine"
    tf-avm-agent refresh-versions
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

from tf_avm_agent.agent import TerraformAVMAgent, generate_terraform
from tf_avm_agent.registry.avm_modules import AVM_MODULES, get_all_categories
from tf_avm_agent.registry.version_fetcher import (
    clear_version_cache,
    fetch_latest_version,
)
from tf_avm_agent.tools.avm_lookup import (
    get_avm_module_info,
    list_available_avm_modules,
    search_avm_modules,
)
from tf_avm_agent.tools.diagram_analyzer import (
    encode_image_to_base64,
    encode_image_from_url,
    get_image_media_type,
    get_filename_from_url,
    is_url,
)
from tf_avm_agent.tools.terraform_generator import write_terraform_files

app = typer.Typer(
    name="tf-avm-agent",
    help="AI Agent for generating Terraform code using Azure Verified Modules (AVM)",
    add_completion=False,
)
console = Console()


@app.command("generate")
def generate_command(
    services: Optional[str] = typer.Option(
        None,
        "--services", "-s",
        help="Comma-separated list of Azure services (e.g., 'vm,storage,keyvault')",
    ),
    diagram: Optional[Path] = typer.Option(
        None,
        "--diagram", "-d",
        help="Path to an architecture diagram image",
        exists=True,
    ),
    name: str = typer.Option(
        ...,
        "--name", "-n",
        help="Name for the Terraform project",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Output directory for generated files",
    ),
    location: str = typer.Option(
        "eastus",
        "--location", "-l",
        help="Azure region for deployment",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive", "-i",
        help="Run in interactive mode with the AI agent",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing files in output directory",
    ),
):
    """
    Generate Terraform code from a list of services or an architecture diagram.

    Examples:
        tf-avm-agent generate -s "vm,storage,keyvault" -n "my-project" -o ./terraform
        tf-avm-agent generate -d architecture.png -n "my-project" -i
    """
    if not services and not diagram:
        console.print("[red]Error: Either --services or --diagram must be provided[/red]")
        raise typer.Exit(1)

    if services and diagram:
        console.print("[yellow]Warning: Both services and diagram provided. Using services.[/yellow]")

    console.print(Panel(f"[bold blue]Terraform AVM Agent[/bold blue]\nGenerating project: {name}"))

    if services:
        # Parse services list
        service_list = [s.strip() for s in services.split(",")]
        console.print(f"\n[cyan]Services:[/cyan] {', '.join(service_list)}")
        console.print(f"[cyan]Location:[/cyan] {location}")

        if interactive:
            # Use the AI agent for interactive generation
            agent = TerraformAVMAgent()
            prompt = f"""Generate a Terraform project with the following specifications:

Project Name: {name}
Services: {', '.join(service_list)}
Location: {location}
{"Output Directory: " + str(output) if output else ""}

Please:
1. Identify the appropriate AVM modules for these services
2. Generate a complete Terraform project
{"3. Write the files to " + str(output) if output else ""}
"""
            with console.status("[bold green]Generating with AI agent..."):
                response = agent.run(prompt)

            console.print("\n[bold green]Agent Response:[/bold green]")
            console.print(Markdown(response))
        else:
            # Direct generation without AI
            with console.status("[bold green]Generating Terraform project..."):
                result = generate_terraform(
                    services=service_list,
                    project_name=name,
                    location=location,
                )

            console.print("\n[bold green]Generated Files:[/bold green]\n")

            for file in result.files:
                console.print(f"\n[cyan]{file.filename}[/cyan]")
                if file.filename.endswith((".tf", ".tfvars.example")):
                    syntax = Syntax(file.content, "hcl", theme="monokai", line_numbers=True)
                    console.print(syntax)
                elif file.filename.endswith(".md"):
                    console.print(Markdown(file.content))
                else:
                    console.print(file.content)

            if output:
                output.mkdir(parents=True, exist_ok=True)
                write_result = write_terraform_files(str(output), result, overwrite)
                console.print(f"\n[bold green]{write_result}[/bold green]")
            else:
                if Confirm.ask("\n[yellow]Would you like to save these files?[/yellow]"):
                    output_dir = Prompt.ask("Output directory", default=f"./{name}")
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
                    write_result = write_terraform_files(output_dir, result, overwrite)
                    console.print(f"\n[bold green]{write_result}[/bold green]")

    elif diagram:
        console.print(f"\n[cyan]Diagram:[/cyan] {diagram}")
        console.print(f"[cyan]Location:[/cyan] {location}")

        agent = TerraformAVMAgent()
        with console.status("[bold green]Analyzing diagram with AI agent..."):
            response = agent.analyze_diagram(
                image_path=str(diagram),
                project_name=name,
                location=location,
                output_dir=str(output) if output else None,
            )

        console.print("\n[bold green]Agent Response:[/bold green]")
        console.print(Markdown(response))


@app.command("chat")
def chat_command(
    azure_openai: bool = typer.Option(
        False,
        "--azure-openai",
        help="Use Azure OpenAI instead of OpenAI",
    ),
):
    """
    Start an interactive chat session with the Terraform AVM Agent.

    The agent can help you:
    - Explore available AVM modules
    - Generate Terraform code
    - Answer questions about Azure infrastructure
    """
    # Auto-detect Azure OpenAI if environment variables are set
    use_azure = azure_openai or bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
    
    if use_azure:
        console.print("[dim]Using Azure OpenAI[/dim]")
    else:
        console.print("[dim]Using OpenAI[/dim]")
    
    console.print(Panel(
        "[bold blue]Terraform AVM Agent - Interactive Mode[/bold blue]\n"
        "Type your questions or requests. Type 'quit' or 'exit' to end the session.\n"
        "Type 'help' for available commands.",
        title="Welcome"
    ))

    agent = TerraformAVMAgent(use_azure_openai=use_azure)

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

            if user_input.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() == "help":
                console.print(Panel(
                    "**Available commands:**\n"
                    "- `list modules` - List all available AVM modules\n"
                    "- `search <query>` - Search for modules\n"
                    "- `info <module>` - Get details about a module\n"
                    "- `load <filepath|url>` - Load and analyze a diagram (local file or URL)\n"
                    "- `generate <services>` - Generate Terraform code\n"
                    "- `clear` - Clear conversation history\n"
                    "- `quit` or `exit` - End the session\n\n"
                    "**Examples:**\n"
                    "- `load ./architecture.png`\n"
                    "- `load https://example.com/diagram.svg`\n"
                    "- 'Generate Terraform for a web app with PostgreSQL database'\n"
                    "- 'What AVM modules are available for networking?'",
                    title="Help"
                ))
                continue

            if user_input.lower() == "clear":
                agent.clear_history()
                console.print("[yellow]Conversation history cleared.[/yellow]")
                continue

            # Handle load diagram command (supports both local files and URLs)
            if user_input.lower().startswith("load "):
                source = user_input.replace("load ", "").strip().strip('"').strip("'")
                
                try:
                    if is_url(source):
                        # Handle URL
                        console.print(f"[dim]Downloading diagram from URL: {source}[/dim]")
                        
                        with console.status("[bold green]Downloading..."):
                            image_data, media_type = encode_image_from_url(source)
                            filename = get_filename_from_url(source)
                        
                        # Store in agent context
                        agent._current_diagram = {
                            "path": source,
                            "data": image_data,
                            "media_type": media_type,
                            "is_url": True
                        }
                        
                        # Send to agent for analysis
                        with console.status("[bold green]Analyzing diagram..."):
                            response = agent.analyze_diagram_from_url(source, filename)
                        
                        console.print(f"\n[bold green]Agent[/bold green]:")
                        console.print(Markdown(response))
                        continue
                    else:
                        # Handle local file
                        file_path = os.path.expanduser(source)
                        
                        if not os.path.exists(file_path):
                            console.print(f"[red]Error: File not found: {file_path}[/red]")
                            continue
                        
                        console.print(f"[dim]Loading diagram: {file_path}[/dim]")
                        
                        # Read and encode the image
                        image_data = encode_image_to_base64(file_path)
                        media_type = get_image_media_type(file_path)
                        
                        # Store in agent context for later use
                        agent._current_diagram = {
                            "path": file_path,
                            "data": image_data,
                            "media_type": media_type,
                            "is_url": False
                        }
                        
                        # Send to agent for analysis
                        with console.status("[bold green]Analyzing diagram..."):
                            response = agent.analyze_diagram(file_path)
                        
                        console.print(f"\n[bold green]Agent[/bold green]:")
                        console.print(Markdown(response))
                        continue
                except Exception as e:
                    console.print(f"[red]Error loading diagram: {e}[/red]")
                    continue

            # Handle special commands
            if user_input.lower().startswith("list modules"):
                category = user_input.replace("list modules", "").strip() or None
                result = list_available_avm_modules(category)
                console.print(Markdown(result))
                continue

            if user_input.lower().startswith("search "):
                query = user_input.replace("search ", "").strip()
                result = search_avm_modules(query)
                console.print(Markdown(result))
                continue

            if user_input.lower().startswith("info "):
                module = user_input.replace("info ", "").strip()
                result = get_avm_module_info(module)
                console.print(Markdown(result))
                continue

            # Use the AI agent for other queries
            with console.status("[bold green]Thinking..."):
                response = agent.run(user_input)

            console.print(f"\n[bold green]Agent[/bold green]:")
            console.print(Markdown(response))

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


@app.command("list-modules")
def list_modules_command(
    category: Optional[str] = typer.Option(
        None,
        "--category", "-c",
        help="Filter by category (compute, networking, storage, database, security, messaging, monitoring, ai)",
    ),
    format: str = typer.Option(
        "table",
        "--format", "-f",
        help="Output format: table, markdown, or json",
    ),
    sync: bool = typer.Option(
        False,
        "--sync", "-s",
        help="Sync with Terraform Registry to discover all available modules",
    ),
):
    """
    List available Azure Verified Modules.

    Examples:
        tf-avm-agent list-modules
        tf-avm-agent list-modules -c networking
        tf-avm-agent list-modules -f json
        tf-avm-agent list-modules --sync  # Fetch all modules from registry
    """
    # Sync with registry if requested
    if sync:
        from tf_avm_agent.registry.avm_modules import sync_modules_from_registry

        with console.status("[bold green]Syncing modules from Terraform Registry..."):
            try:
                sync_modules_from_registry()
                console.print("[green]✓ Synced modules from registry[/green]\n")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not sync from registry: {e}[/yellow]\n")

    if format == "json":
        import json

        modules = AVM_MODULES
        if category:
            modules = {k: v for k, v in modules.items() if v.category == category}

        output = {}
        for name, module in modules.items():
            output[module.registry_name] = {
                "source": module.source,
                "version": module.version,
                "category": module.category,
                "description": module.description,
                "aliases": module.aliases,
            }
        console.print(json.dumps(output, indent=2))

    elif format == "markdown":
        result = list_available_avm_modules(category)
        console.print(Markdown(result))

    else:  # table format
        table = Table(title="Azure Verified Modules")
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="green")
        table.add_column("Description", style="white")
        table.add_column("Version", style="yellow")

        modules = AVM_MODULES
        if category:
            modules = {k: v for k, v in modules.items() if v.category == category}

        # Deduplicate by registry_name, keeping the one with the higher version
        unique_modules: dict[str, tuple[str, any]] = {}
        for key, module in modules.items():
            reg_name = module.registry_name
            if reg_name not in unique_modules or module.version > unique_modules[reg_name][1].version:
                unique_modules[reg_name] = (key, module)

        for reg_name, (key, module) in sorted(unique_modules.items(), key=lambda x: (x[1][1].category, x[0])):
            table.add_row(
                module.registry_name,
                module.category,
                module.description[:60] + "..." if len(module.description) > 60 else module.description,
                module.version,
            )

        console.print(table)
        console.print(f"\n[dim]Total: {len(unique_modules)} modules[/dim]")

        if not category:
            console.print(f"[dim]Categories: {', '.join(sorted(get_all_categories()))}[/dim]")


@app.command("search")
def search_command(
    query: str = typer.Argument(..., help="Search query"),
):
    """
    Search for Azure Verified Modules.

    Examples:
        tf-avm-agent search database
        tf-avm-agent search "kubernetes"
    """
    result = search_avm_modules(query)
    console.print(Markdown(result))


@app.command("info")
def info_command(
    module: str = typer.Argument(..., help="Module name or alias"),
):
    """
    Get detailed information about an AVM module.

    Examples:
        tf-avm-agent info virtual_machine
        tf-avm-agent info aks
        tf-avm-agent info storage
    """
    result = get_avm_module_info(module)
    console.print(Markdown(result))


@app.command("categories")
def categories_command():
    """
    List all available module categories.
    """
    categories = get_all_categories()

    table = Table(title="Module Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Module Count", style="green")

    for category in sorted(categories):
        count = len([m for m in AVM_MODULES.values() if m.category == category])
        table.add_row(category, str(count))

    console.print(table)


@app.command("refresh-versions")
def refresh_versions_command(
    module_name: Optional[str] = typer.Argument(
        None,
        help="Specific module to refresh (optional, refreshes all if not provided)",
    ),
    clear_cache: bool = typer.Option(
        False,
        "--clear-cache", "-c",
        help="Clear all cached versions before refreshing",
    ),
):
    """
    Refresh module versions from the Terraform Registry.

    Examples:
        tf-avm-agent refresh-versions                    # Refresh all modules
        tf-avm-agent refresh-versions virtual_machine    # Refresh specific module
        tf-avm-agent refresh-versions --clear-cache      # Clear cache and refresh all
    """
    if clear_cache:
        clear_version_cache()
        console.print("[yellow]Cleared version cache[/yellow]")

    if module_name:
        # Refresh specific module
        from tf_avm_agent.registry.avm_modules import get_module_by_service

        module = get_module_by_service(module_name)
        if not module:
            console.print(f"[red]Module '{module_name}' not found[/red]")
            raise typer.Exit(1)

        with console.status(f"[bold green]Fetching latest version for {module.name}..."):
            version = fetch_latest_version(module.source)

        if version:
            console.print(f"[green]✓[/green] {module.name}: {version}")
        else:
            console.print(f"[yellow]![/yellow] {module.name}: Failed to fetch (using fallback: {module.version})")
    else:
        # Refresh all modules
        console.print(f"[cyan]Refreshing versions for {len(AVM_MODULES)} modules...[/cyan]\n")

        success_count = 0
        fail_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching versions...", total=len(AVM_MODULES))

            for name, module in AVM_MODULES.items():
                progress.update(task, description=f"Fetching {name}...")
                version = fetch_latest_version(module.source)

                if version:
                    success_count += 1
                else:
                    fail_count += 1

                progress.advance(task)

        console.print(f"\n[green]✓ Successfully refreshed: {success_count}[/green]")
        if fail_count > 0:
            console.print(f"[yellow]! Failed to fetch: {fail_count} (using fallback versions)[/yellow]")


@app.command("sync-modules")
def sync_modules_command():
    """
    Synchronize module list from the official AVM published modules list.

    This command fetches all 105 published AVM modules from the authoritative list
    at https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/
    and fetches their latest versions from the Terraform Registry.

    Examples:
        tf-avm-agent sync-modules
    """
    from tf_avm_agent.registry.avm_modules import sync_modules_from_registry
    from tf_avm_agent.registry.module_discovery import (
        fetch_published_modules_sync,
        save_discovered_modules,
    )
    from tf_avm_agent.registry.published_modules import PUBLISHED_AVM_MODULES

    console.print(Panel("[bold blue]Syncing AVM Modules (Official Published List)[/bold blue]"))
    console.print(f"[dim]Source: https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/[/dim]\n")

    with console.status("[bold green]Fetching versions for all 105 published modules..."):
        try:
            discovered = fetch_published_modules_sync()
            save_discovered_modules(discovered)
            console.print(f"[green]✓ Fetched {len(discovered)} published AVM modules[/green]")
        except Exception as e:
            console.print(f"[red]Error fetching modules: {e}[/red]")
            raise typer.Exit(1)

    with console.status("[bold green]Updating local registry..."):
        try:
            modules = sync_modules_from_registry()
        except Exception as e:
            console.print(f"[red]Error syncing modules: {e}[/red]")
            raise typer.Exit(1)

    # Deduplicate by registry_name for accurate count
    unique_modules: dict[str, any] = {}
    for key, module in modules.items():
        reg_name = module.registry_name
        if reg_name not in unique_modules or module.version > unique_modules[reg_name].version:
            unique_modules[reg_name] = module

    console.print(f"[green]✓ Total unique modules: {len(unique_modules)}[/green]")

    # Show category breakdown
    table = Table(title="Module Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")

    categories = {}
    for module in unique_modules.values():
        cat = module.category
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items()):
        table.add_row(cat, str(count))

    console.print(table)

    console.print(f"\n[dim]Modules cached at ~/.cache/tf-avm-agent/[/dim]")


@app.command("version")
def version_command():
    """Show the version of tf-avm-agent."""
    from tf_avm_agent import __version__
    console.print(f"tf-avm-agent version {__version__}")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
