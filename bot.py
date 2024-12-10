import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime
import asyncio

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GENERAL_CHANNEL_ID = int(os.getenv('GENERAL_CHANNEL_ID'))
SUPPORT_CHANNEL_ID = int(os.getenv('SUPPORT_CHANNEL_ID'))
LOGS_CHANNEL_ID = int(os.getenv('LOGS_CHANNEL_ID'))
AUTHORIZED_ROLE_ID = int(os.getenv('AUTHORIZED_ROLE_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!c', intents=intents)

# Colors for embeds
BLUE = 0x3498db
GREEN = 0x2ecc71
ORANGE = 0xe67e22
RED = 0xe74c3c
WHITE = 0xFFFFFF

class SupportBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{self.bot.user} has connected to Discord!')
        await self.send_startup_log()
        await self.bot.tree.sync()
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="coolLabs"))

    async def send_startup_log(self):
        logs_channel = self.bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            embed = discord.Embed(title="Connection established", color=GREEN)
            embed.add_field(name="App Name", value=self.bot.user.name, inline=False)
            embed.add_field(name="App ID", value=self.bot.user.id, inline=False)
            embed.add_field(name="Initial Connection Time", value=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
            
            if self.bot.guilds:
                embed.add_field(name="Server Name", value=self.bot.guilds[0].name, inline=False)
                embed.add_field(name="Server ID", value=self.bot.guilds[0].id, inline=False)
            
            embed.add_field(name="Total Servers", value=len(self.bot.guilds), inline=False)
            
            await logs_channel.send(embed=embed)
        else:
            print(f"Warning: Logs channel with ID {LOGS_CHANNEL_ID} not found.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
    
        if message.channel.id == GENERAL_CHANNEL_ID and message.reference and self.bot.user in message.mentions:
            authorized_role = discord.utils.get(message.guild.roles, id=AUTHORIZED_ROLE_ID)
            if authorized_role in message.author.roles:
                await self.handle_support_request(message)
                await message.delete()  # Delete the bot ping message
            else:
                # Directly delete the message without sending a response
                await message.delete()

        if message.author == self.bot.user:
            return
        await self.bot.process_commands(message)

    async def handle_support_request(self, message):
        try:
            replied_message = await message.channel.fetch_message(message.reference.message_id)

            if replied_message.author == self.bot.user:
                await message.delete()
                return
            
            messages_to_move = await self.get_messages_to_move(message, replied_message)

            content = self.compile_content(messages_to_move)

            support_channel = self.bot.get_channel(SUPPORT_CHANNEL_ID)
            if not support_channel or not isinstance(support_channel, discord.ForumChannel):
                raise ValueError(f"Support channel with ID {SUPPORT_CHANNEL_ID} not found or is not a ForumChannel")

            title = self.generate_title(messages_to_move, replied_message)

            files = await self.get_files(messages_to_move)

            forum_thread = await self.create_forum_thread(support_channel, title, content, replied_message, files)

            thread_message = forum_thread.message
            if thread_message:
                await self.send_support_embed(thread_message)
                await self.send_general_notification(message, replied_message, thread_message)
                await self.send_log(message, replied_message, content, files, thread_message)

            await self.delete_original_messages(messages_to_move)

        except Exception as e:
            await self.handle_error(e)

    async def get_messages_to_move(self, message, replied_message):
        messages_to_move = [replied_message]
        async for msg in message.channel.history(limit=None, after=replied_message.created_at):
            if msg.author == replied_message.author and msg.created_at < message.created_at:
                messages_to_move.append(msg)
            elif msg.id == message.id:
                break
        return sorted(messages_to_move, key=lambda x: x.created_at)

    def compile_content(self, messages):
        return "\n\n".join([msg.content for msg in messages if msg.content.strip()])

    def generate_title(self, messages, replied_message):
        title = messages[0].content[:100] if messages[0].content else f"Support request from {replied_message.author.name}"
        return title.strip() or "Support Request"

    async def get_files(self, messages):
        files = []
        for msg in messages:
            for attachment in msg.attachments:
                try:
                    files.append(await attachment.to_file())
                except discord.HTTPException:
                    print(f"Failed to download attachment: {attachment.filename}")
        return files

    async def create_forum_thread(self, support_channel, title, content, replied_message, files):
        initial_message = f"{replied_message.author.mention} need some assistance with Coolify!"
        if content:
            initial_message += f"\n\n__**Original Message:**__\n{content}"
        if files:
            initial_message += f"\n\nAttached **{len(files)}** {'file' if len(files) == 1 else 'files'}"

        thread = await support_channel.create_thread(
            name=title,
            content=initial_message,
            files=files if files else []
        )
        return thread

    async def send_support_embed(self, thread_message):
        support_embed = discord.Embed(title="Note", color=WHITE)
        support_embed.description = (
            "Please remember that everyone in this server helps others voluntarily.\n\n "
            "Do not ping anyone (including Admins, Mods, Community Experts, or Developers) for attention, "
            "and avoid posting your question or request in any other channel.\n\n"
            "Failure to follow these guidelines may result in temporary exclusion from the server.\n\n"
            "While you wait, you can refer to our documentation for potential solutions to your issue view our [documentation](https://coolify.io/docs/)"
        )
        await thread_message.channel.send(embed=support_embed)

    async def send_general_notification(self, message, replied_message, thread_message):
        general_channel = self.bot.get_channel(GENERAL_CHANNEL_ID)
        if general_channel:
            notify_message = f"Hey {replied_message.author.mention} to prevent your question from getting lost we moved it to {thread_message.jump_url}, please continue the conversation in that post."
            await general_channel.send(notify_message)
        else:
            print(f"General channel with ID {GENERAL_CHANNEL_ID} not found.")

    async def send_log(self, message, replied_message, content, files, thread_message):
        logs_channel = self.bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            log_embed = discord.Embed(title="Message moved to Support channel successfully.", color=GREEN)
            log_embed.add_field(name="Message Owner", value=replied_message.author.mention, inline=False)
            log_embed.add_field(name="Moved by", value=message.author.mention, inline=False)
            log_embed.add_field(name="Total Characters", value=len(content), inline=False)
            log_embed.add_field(name="Total Attachments", value=f"{len(files)} {'file' if len(files) == 1 else 'files'}", inline=False)
            log_embed.add_field(name="Support Post", value=f"{thread_message.jump_url}", inline=False)
            await logs_channel.send(embed=log_embed)
            
    async def delete_original_messages(self, messages):
        for msg in messages:
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                pass
            await asyncio.sleep(0.5)  # To avoid rate limiting

    async def handle_error(self, error):
        error_message = f"An error occurred while handling a support request: {error}"
        print(error_message)
        logs_channel = self.bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            await logs_channel.send(embed=discord.Embed(description=error_message, color=RED))

    @app_commands.command(name="ping", description="Check the bot's status")
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency * 1000  # Convert to milliseconds
        api_response_time = round(latency, 2)
        embed = discord.Embed(title="I'm Alive!", description=f"**Response time:** {api_response_time}ms", color=GREEN)
        embed.set_footer(text="Version v1.1 Stable")
        await interaction.response.send_message(embed=embed)

async def main():
    async with bot:
        await bot.add_cog(SupportBot(bot))
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())