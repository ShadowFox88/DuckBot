from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Optional,
)

import discord
from discord.ext import commands

from utils import DuckCog
from utils.context import DuckContext
from utils.time import human_join

if TYPE_CHECKING:
    from bot import DuckBot

# Leo im gonna be honest I have 0 clue
# if any of these commands work I havent tested any of them yet.
# Feel free to if you get a chance

class PrefixChanges(DuckCog):
    
    @commands.group(name='prefix', aliases=['prefixes'], invoke_without_command=True)
    @commands.guild_only()
    async def prefix(self, ctx: DuckContext, *, prefix: Optional[str] = None) -> Optional[discord.Message]:
        """
        Adds a prefix for this server (you can have up to 25 prefixes).
        
        Parameters
        ----------
        prefix: Optional[:class:`str`]
            The prefix to add to the bot. If no prefix is given,
            the current prefixes will be shown.
        """
        if ctx.invoked_subcommand:
            return
        
        if prefix is None:
            prefixes = await self.bot.get_prefix(ctx.message, raw=True)
            embed = discord.Embed(title='Current Prefixes', description='\n'.join(prefixes))
            return await ctx.send(embed=embed)

        guild = ctx.guild
        if not guild: # Safty net for type checker
            return
        
        async with self.bot.safe_connection() as conn:
            data = await conn.fetchrow('SELECT prefixes FROM guilds WHERE guild_id = $1', guild.id)
        
            if not data:
                # This server had no existing prefix data but wants it, let's create it
                query = 'INSERT INTO prefixes(guild_id, prefixes) VALUES ($1, $2) RETURNING prefixes'
                args = (guild.id, [prefix])
            else:
                # This server had existing prefix data, append it onto the array of prefixes
                query = 'UPDATE prefixes SET prefixes = array_append(prefixes, $1) WHERE guild_id = $2 RETURNING prefixes'
                args = (prefix, guild.id)
                
            result = await conn.fetchrow(query, *args)
        
        prefixes = result['prefixes']
        
        # Cleanup bot cache before anything else
        self.bot.prefix_cache[guild.id] = prefixes
        
        embed = discord.Embed(
            title=f'Prefix "{prefix}" added.',
            description=f'I\'ve added the prefix `{prefix}` to this server.\n'
        )
        embed.add_field(name='Prefixes', value=human_join(prefixes, final='and'))
        return await ctx.send(embed=embed)
    
    @prefix.command(name='clear', aliases=['wipe', 'whipe'])
    @commands.guild_only()
    async def prefix_clear(self, ctx: DuckContext) -> Optional[discord.Message]:
        """
        Clears all prefixes from this server, restting them to default.
        """
        guild = ctx.guild
        if guild is None:
            return
        
        async with self.bot.safe_connection() as conn:
            data = await conn.fetchrow('SELECT prefixes FROM guilds WHERE guild_id = $1', guild.id) 
            
            if not data or not data.get('prefixes'):
                # NOTE: Leo embed this im too lazy
                return await ctx.send('This server has no prefixes to clear.')
            
            result = await conn.fetchrow('UPDATE guilds SET prefixes = $1 WHERE guild_id = $2 RETURNING prefixes', [], guild.id)
        
        # Cleanup bot cache before anything else
        self.bot.prefix_cache.pop(guild.id, None)
        
        prefixes = result['prefixes']
        embed = discord.Embed(
            title=f'Cleared {len(prefixes)} prefixes.',
            description=f'I\'ve cleared all prefixes from this server.\n'
        )
        embed.add_field(name='Old Prefixes', value=human_join(prefixes, final='and'))
        return await ctx.send(embed=embed)
      
    @discord.utils.copy_doc(prefix)  
    @prefix.command(name='add', aliases=['append'])
    @commands.guild_only()
    async def prefix_add(self, ctx: DuckContext, *, prefix: str) -> Optional[discord.Message]:
        return await ctx.invoke(self.prefix, prefix=prefix)

    @prefix.command(name='remove', aliases=['delete', 'del', 'rm'])
    @commands.guild_only()
    async def prefix_remove(self, ctx: DuckContext, *, prefix: str) -> Optional[discord.Message]:
        """
        Removes a prefix from the bots prefixes.
        
        Parameters
        ----------
        prefix: :class:`str`
            The prefix to remove from the bots prefixes.
        """
        guild = ctx.guild
        if not guild:
            return
        
        prefixes = await self.bot.get_prefix(ctx.message, raw=True)
        if prefix not in prefixes:
            # NOTE: Add fuzzy matching here to suggest a prefix that might be the one they want
            embed = discord.Embed(
                title='Oh no!',
                description='This prefix is not in the list of prefixes. Are you sure you spelt it correct?'
            )
            return await ctx.reply(embed=embed)

        async with self.bot.safe_connection() as conn:
            await conn.execute('UPDATE guilds SET prefixes = array_remove(prefixes, $1) WHERE guild_id = $2', prefix, guild.id)
        
        # Cleanup cache before anything else
        try:
            self.bot.prefix_cache[guild.id].remove(prefix)
        except (KeyError, ValueError):
            # No guild cache or prefix not in the cache
            pass
        
        prefixes.remove(prefix)
        
        embed = discord.Embed(
            title='Prefix removed',
            description=f'The prefix `{prefix}` has been removed from this server.'
        )
        embed.add_field(name='Current Prefixes', value=human_join(prefixes, final='and'))
        return await ctx.send(embed=embed)

def setup(bot: DuckBot) -> None:
    return bot.add_cog(PrefixChanges(bot))