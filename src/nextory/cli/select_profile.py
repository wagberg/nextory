"""CLI tool for selecting and saving Nextory profile."""

import asyncio
from typing import Optional

import aiohttp
import click

from nextory import NextoryClient
from nextory.config import ProfileConfig


async def select_profile_async(
    username: str,
    password: str,
    profile_name: Optional[str] = None,
) -> None:
    """Select and save profile configuration."""
    async with aiohttp.ClientSession() as session:
        async with NextoryClient(
            session=session,
            username=username,
            password=password,
            auto_select_profile=True,
        ) as client:
            login_key = None
            selected_profile = None
            # Trigger a login
            login_token = await client.login(username, password)

            # List profiles 
            profiles = await client.get_profiles()

            if not profiles.profiles:
                click.echo("No profiles found.")
                return

            # If profile_name is given, try to find that profile and get the login_key
            if profile_name is not None:
                for profile in profiles.profiles:
                    if profile.name == profile_name:
                        selected_profile = profile
                        break
            else:
                # Interactive menu to list the profile names and selection
                options: list[str] = []
                for profile in profiles.profiles:
                    main_marker = " (main)" if profile.is_main else ""
                    s = f"{profile.name}{main_marker}"
                    options.append(s)
                    click.echo(s)


                selected_index = click.prompt(
                    "Select a profile",
                    type=click.Choice(range(len(options))),
                    show_choices=True,
                    value_proc=lambda x: options[int(x)]
                )

                selected_profile = profiles.profiles[int(selected_index)]
                login_key = selected_profile.login_key
        if not selected_profile:
            click.echo("No profile selected")
            return
        if not login_key or not client.login_token or not client.profile_token:
            click.echo("Could not extract login_key")
            return

        profile_token = await client.select_profile(selected_profile.login_key)
        
        # Save configuration
        config = ProfileConfig(
            login_token=client.login_token,
            login_key=selected_profile.login_key,
            profile_token=profile_token,
        )
        config.save()
        click.echo(f"\nProfile '{selected_profile.name} {selected_profile.surname}' saved to {config.get_config_path()}")


@click.command()
@click.option("--username", prompt=True, help="Nextory username/email")
@click.option("--password", prompt=True, hide_input=True, help="Nextory password")
@click.option("--profile-name", help="Profile name to select")
def main(username: str, password: str, profile_name: Optional[str]):
    """Select and save Nextory profile configuration."""
    asyncio.run(select_profile_async(username, password, profile_name))


if __name__ == "__main__":
    main()
