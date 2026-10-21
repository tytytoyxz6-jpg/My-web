import datetime
import discord
import asyncio
import time
import os
from collections import defaultdict, deque
from datetime import timedelta
from discord.ext import commands
from datetime import timedelta
from typing import Optional
import string
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import arabic_reshaper
from bidi.algorithm import get_display
LEVEL_UP_CHANNEL_ID = 1560384493439680594
MESSAGE_LOGS_ID= 1542372884973101127
BAN_LOGS_ID =1542338310624645261
KICK_LOGS_ID =1542374182342492191
ROLES_LOGS_ID = 1545635585555701801
TIMEOUT_LOGS_ID = 1542338752804819024

TOKEN = os.environ.get('My_token')



intents = discord.Intents.default()
intents.message_content = True
intents.members = True

clint = commands.Bot(command_prefix="/", intents=intents)



@clint.event
async def on_ready():
  print(f"bot is warking{clint.user}")
  await clint.tree.sync()



track_pepole = {}
wating = None
old_roles = {}
warns = {}
exp_message = {}

# =========================
# التحقق من الرتب
# =========================

def can_moderate(actor, target):
    if actor.id == target.id:
        return False

    if actor.id == actor.guild.owner_id:
        return True

    return actor.top_role > target.top_role

####################
# خاص ب صور الlevel
####################
async def make_welcome_card(member):
    card = Image.open("welcome.jpg").convert("RGB")

    avatar_bytes = await member.display_avatar.read()
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGB")

    avatar = avatar.resize((306, 427))
    card.paste(avatar, (51, 57))

    output = BytesIO()
    card.save(output, format="PNG")
    output.seek(0)

    return output
####################
# خاص ب صور الlevel
####################


async def make_level_card(member, level):
    card = Image.open("Level_up.png").convert("RGBA")
    draw = ImageDraw.Draw(card)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    # صورة العضو
    avatar_bytes = await member.display_avatar.read()
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((400, 400))

    mask = Image.new("L", (400, 400), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 399, 399), fill=255)

    card.paste(avatar, (370, 340), mask)

    
    # اسم العضو
    name_font = ImageFont.truetype(font_path, 52)

    name = arabic_reshaper.reshape(member.display_name)
    name = str(get_display(name))

    draw.text(
        (570, 835),
        name,
        fill="#A020F0",
        font=name_font,
        anchor="mm"
    )
  



    # المستوى
    level_font = ImageFont.truetype(font_path,60 )
    draw.text(
        (570, 940),
        f"LEVEL {level}",
        fill="#A020F0",
        font=level_font,
        anchor="mm"
    )

    # رسالة التهنئة بالعربي
    arabic_text = f"مبروك بقيت لفل {level}!"
    arabic_text = arabic_reshaper.reshape(arabic_text)
    arabic_text = str(get_display(arabic_text))

    arabic_font = ImageFont.truetype(font_path, 49)
    draw.text(
        (570, 1120),
        arabic_text,
        fill="#A020F0",
        font=arabic_font,
        anchor="mm"
    )

    output = BytesIO()
    card.save(output, format="PNG")
    output.seek(0)

    return output
  
#####################
# خاص ب صور الlevel
#####################
@clint.event
async def on_member_join(member):
    channel = clint.get_channel(1542633772837511328)

    if not isinstance(channel, discord.TextChannel):
        return

    image = await make_welcome_card(member)
  
    await channel.send(
   f"أهلاً بيك يا {member.mention} ❤️\n"
    f"أنت العضو رقم {member.guild.member_count} في السيرفر!",
    file=discord.File(image, filename="welcome.png")
)


    
# =========================
# أدوات سجل التدقيق
# =========================
            
# =========================
# أدوات سجل التدقيق
# =========================

async def find_audit_entry(guild, action, target_id):
    try:
        async for entry in guild.audit_logs(limit=10, action=action):
            age = abs((discord.utils.utcnow() - entry.created_at).total_seconds())

            if (
                getattr(entry.target, "id", None) == target_id
                and age < 20
            ):
                return entry

    except discord.Forbidden:
        print("⚠️ [تحذير]: البوت يحتاج إلى صلاحية View Audit Log.")

    except discord.HTTPException as error:
        print(f"❌ [خطأ في Audit Log]: {error}")

    return None


async def send_log(channel_id, embed):
    if not channel_id:
        return
    
    channel = clint.get_channel(channel_id)
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as error:
            print(f"❌ [خطأ في إرسال الـ Log]: {error}")


def make_action_embed(title, color, target, moderator, reason=None):
    embed = discord.Embed(
        title=title,
        color=color,
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 العضو المستهدف",
        value=f"{target} (`{target.id}`)",
        inline=False
    )

    executor = (
        f"{moderator.mention} (`{moderator.id}`)"
        if moderator else "تعذّر تحديد المنفّذ"
    )

    embed.add_field(
        name="🛡️ منفّذ الإجراء",
        value=executor,
        inline=False
    )

    if reason:
        embed.add_field(
            name="📝 السبب",
            value=reason[:1024],
            inline=False
        )

    return embed


# =========================
# أرشيف الرسائل (الممسوحة والمتعدلة)
# =========================

@clint.event
async def on_message_delete(message):
    if message.author.bot:
        return

    entry = await find_audit_entry(
        message.guild,
        discord.AuditLogAction.message_delete,
        message.author.id
    )

    embed = discord.Embed(
        title="🗑️ تم حذف رسالة",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 صاحب الرسالة",
        value=f"{message.author.mention} (`{message.author.id}`)",
        inline=False
    )

    embed.add_field(
        name="📍 القناة",
        value=f"{message.channel.mention}",
        inline=False
    )

    deleter = entry.user.mention if entry else message.author.mention
    embed.add_field(
        name="🛡️ حُذفت بواسطة",
        value=deleter,
        inline=False
    )

    content = message.content if message.content else "*الرسالة لا تحتوي على نص (صورة أو مرفق)*"
    embed.add_field(
        name="💬 محتوى الرسالة",
        value=content[:1024],
        inline=False
    )

    if message.attachments:
        embed.set_image(url=message.attachments[0].url)

    await send_log(MESSAGE_LOGS_ID, embed)


@clint.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return

    embed = discord.Embed(
        title="✏️ تم تعديل رسالة",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="👤 صاحب الرسالة",
        value=f"{before.author.mention} (`{before.author.id}`)",
        inline=False
    )

    embed.add_field(
        name="📍 القناة",
        value=f"{before.channel.mention} | [الذهاب للرسالة]({after.jump_url})",
        inline=False
    )

    embed.add_field(
        name="💬 قبل التعديل",
        value=before.content[:1024] if before.content else "*فارغة*",
        inline=False
    )

    embed.add_field(
        name="💬 بعد التعديل",
        value=after.content[:1024] if after.content else "*فارغة*",
        inline=False
    )

    await send_log(MESSAGE_LOGS_ID, embed)


# =========================
# إضافة وإزالة رولات الأعضاء + Timeout
# =========================

@clint.event
async def on_member_update(before, after):
    old_roles = {role.id: role for role in before.roles}
    new_roles = {role.id: role for role in after.roles}

    added_roles = [
        role for role_id, role in new_roles.items()
        if role_id not in old_roles
    ]

    removed_roles = [
        role for role_id, role in old_roles.items()
        if role_id not in new_roles
    ]

    role_entry = None
    if added_roles or removed_roles:
        role_entry = await find_audit_entry(
            after.guild,
            discord.AuditLogAction.member_role_update,
            after.id
        )

    for role in added_roles:
        embed = discord.Embed(
            title="🟢 تمت إضافة رتبة لعضو",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 العضو",
            value=f"{after.mention} (`{after.id}`)",
            inline=False
        )
        embed.add_field(
            name="🎭 الرتبة",
            value=f"{role.name} (`{role.id}`)",
            inline=False
        )
        embed.add_field(
            name="🛡️ المنفّذ",
            value=(
                f"{role_entry.user.mention} (`{role_entry.user.id}`)"
                if role_entry else "تعذّر تحديد المنفّذ"
            ),
            inline=False
        )

        await send_log(ROLES_LOGS_ID, embed)

    for role in removed_roles:
        embed = discord.Embed(
            title="🔴 تمت إزالة رتبة من عضو",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(
            name="👤 العضو",
            value=f"{after.mention} (`{after.id}`)",
            inline=False
        )
        embed.add_field(
            name="🎭 الرتبة",
            value=f"{role.name} (`{role.id}`)",
            inline=False
        )
        embed.add_field(
            name="🛡️ المنفّذ",
            value=(
                f"{role_entry.user.mention} (`{role_entry.user.id}`)"
                if role_entry else "تعذّر تحديد المنفّذ"
            ),
            inline=False
        )

        await send_log(ROLES_LOGS_ID, embed)

    old_timeout = before.timed_out_until
    new_timeout = after.timed_out_until

    if old_timeout != new_timeout:
        timeout_entry = await find_audit_entry(
            after.guild,
            discord.AuditLogAction.member_update,
            after.id
        )

        if new_timeout is not None:
            embed = discord.Embed(
                title="⏳ تم عمل Timeout لعضو",
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="👤 العضو المستهدف",
                value=f"{after.mention} (`{after.id}`)",
                inline=False
            )

            embed.add_field(
                name="🛡️ منفّذ الإجراء",
                value=(
                    f"{timeout_entry.user.mention} (`{timeout_entry.user.id}`)"
                    if timeout_entry else "تعذّر تحديد المنفّذ"
                ),
                inline=False
            )

            if timeout_entry and timeout_entry.reason:
                embed.add_field(
                    name="📝 السبب",
                    value=timeout_entry.reason[:1024],
                    inline=False
                )

            embed.add_field(
                name="🕒 ينتهي في",
                value=f"<t:{int(new_timeout.timestamp())}:F>",
                inline=False
            )

            await send_log(TIMEOUT_LOGS_ID, embed)

        else:
            embed = discord.Embed(
                title="✅ تم فك Timeout عن عضو",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )

            embed.add_field(
                name="👤 العضو المستهدف",
                value=f"{after.mention} (`{after.id}`)",
                inline=False
            )

            embed.add_field(
                name="🛡️ منفّذ الإجراء",
                value=(
                    f"{timeout_entry.user.mention} (`{timeout_entry.user.id}`)"
                    if timeout_entry else "تعذّر تحديد المنفّذ"
                ),
                inline=False
            )

            if timeout_entry and timeout_entry.reason:
                embed.add_field(
                    name="📝 السبب",
                    value=timeout_entry.reason[:1024],
                    inline=False
                )

            await send_log(TIMEOUT_LOGS_ID, embed)


# =========================
# إنشاء رتبة جديدة
# =========================

@clint.event
async def on_guild_role_create(role):
    entry = await find_audit_entry(
        role.guild,
        discord.AuditLogAction.role_create,
        role.id
    )

    embed = discord.Embed(
        title="✨ تم إنشاء رتبة جديدة",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="🎭 اسم الرتبة",
        value=f"{role.name} (`{role.id}`)",
        inline=False
    )

    embed.add_field(
        name="🛡️ منشئ الرتبة",
        value=(
            f"{entry.user.mention} (`{entry.user.id}`)"
            if entry else "تعذّر تحديد المنشئ"
        ),
        inline=False
    )

    await send_log(ROLES_LOGS_ID, embed)


# =========================
# الكيك
# =========================

@clint.event
async def on_member_remove(member):
    entry = await find_audit_entry(
        member.guild,
        discord.AuditLogAction.kick,
        member.id
    )

    if entry is None:
        return

    embed = make_action_embed(
        "👢 تم طرد عضو",
        discord.Color.orange(),
        member,
        entry.user,
        entry.reason
    )

    await send_log(KICK_LOGS_ID, embed)


# =========================
# البان
# =========================

@clint.event
async def on_member_ban(guild, user):
    entry = await find_audit_entry(
        guild,
        discord.AuditLogAction.ban,
        user.id
    )

    embed = make_action_embed(
        "🔨 تم حظر عضو",
        discord.Color.red(),
        user,
        entry.user if entry else None,
        entry.reason if entry else None
    )

    await send_log(BAN_LOGS_ID, embed)


# =========================
# فك البان
# =========================

@clint.event
async def on_member_unban(guild, user):
    entry = await find_audit_entry(
        guild,
        discord.AuditLogAction.unban,
        user.id
    )

    embed = make_action_embed(
        "🔓 تم فك حظر عضو",
        discord.Color.green(),
        user,
        entry.user if entry else None,
        entry.reason if entry else None
    )

    await send_log(BAN_LOGS_ID, embed)
    


    
            
    

            
    
#####################
@clint.event
async def on_message(message):
  global wating

  
  if message.author == clint.user:
    return

    
    
  if message.content==("استهدو بالله"):
    await message.channel.send("صلو علي النبي ")
   
  pic_id =1542362608911392788
  if  message.content.startswith("لواء صور هنا")and message.mentions:
    member = message.mentions[0]
    pic= message.guild.get_role(pic_id)
    if pic is None:
      
     await message.channel.send("مش لاقي رتبة الصور، اتأكد من الـ ID")
     return
    if pic not in member.roles:
      
     if message.author.guild_permissions.manage_roles:
      
      
       if not can_moderate(message.author, member):
         await message.channel.send("أكبر الأول يا حبيبي 😂")
         return
       else:
         await member.add_roles(pic)
         await message.channel.send(f"حاضر يا حبيبي {member.mention} مبروك")
     else:
      await message.channel.send("بس يا حبيبي")
    else:
     await message.channel.send("طب مهو معاه رول صور يسطا")
      


    
  # =========================
  # نظام ال exp / id الصور فوق شويه 
  # ========================
  user_id = message.author.id
  sound_id = 1544732642606583910
  share_id = 1544743329755963453
  if user_id not in exp_message:
    exp_message[user_id] = {"message": 0, "Level": 0}

  exp_message[user_id]["message"] += 1

  number_of_message = exp_message[user_id]["message"]
  Level = exp_message[user_id]["Level"]

  if number_of_message % 100== 0 and Level < 100:
    exp_message[user_id]["Level"] += 1
    Level = exp_message[user_id]["Level"]

    channel = clint.get_channel(LEVEL_UP_CHANNEL_ID)

    if channel is not None:
      image = await make_level_card(message.author, Level)
      
      if isinstance(channel, discord.TextChannel):
        
       await channel.send(
        content=f"🎉 مبروك {message.author.mention}وصلت\n# Level{Level}",
        file=discord.File(image, filename="level_up.png")
      )
    else:
      print("مش لاقي تشانل الليفل أب، راجع الـ ID")
    ###########
    # اعطاء صور
    ###########
  if exp_message[user_id]["message"]==300:
      pic= message.guild.get_role(pic_id)
      if pic is not None:
        if pic not in message.author.roles:
         await message.author.add_roles(pic)
         await message.channel.send(f"مبروك بقيت صحفي معاك رول صور {message.author.mention} \n# Level {Level}")
        else :
          await message.channel.send(f"العضو{message.author.mention} وصل {exp_message[user_id]['message']} رساله بس مش هديله رول صور عشان معاه")
  ##############
  # اعطاء ساوند بورد
  ##############
  if exp_message[user_id]["message"]==100:
    sound= message.guild.get_role(sound_id)
    if sound is not None:
      if sound not in message.author.roles:
        await message.author.add_roles(sound)
        await message.channel.send(f"مبروك للعضو {message.author.mention} معاك رول ساوند بورد\n# Level {Level}")
      else:
        await message.channel.send(f"العضو {message.author.mention} وصل \n# Level {Level} بس مش هديه رول ساوند عشان معاه")
##############
#اعطاء شير سكرين  
##############

  if exp_message[user_id]["message"]==200:
    share=message.guild.get_role(share_id)
    if share is not None :
      if share not in message.author.roles:
        await message.author.add_roles(share)
        await message.channel.send(f"مبروك للعضو {message.author.mention} معاك رول شير سكرين\n# Level {Level}")
      else: 
        await message.channel.send(f"العضو {message.author.mention} بعت 200 رساله بس مش هديه رول شير سكرين عشان معاه")
    else:
      await message.channel.send("انا مش عارف الاقي الرول ")
        
# =========================
# نظام البامب
# =========================
    
  if message.author.id == 302050872383242240:
    
    if message.interaction_metadata:
      
        user = message.interaction_metadata.user
        await message.channel.send(f"تسلم يا <@{user.id}> علي البامب هفكرك كمان ساعتين")
        async def remind_bump():
          await asyncio.sleep(7200)
          await message.channel.send(f"يا {user.mention} وقت البامب جه")
        asyncio.create_task(remind_bump())
###################
#
#   قفل الشات بالكلام
#
###################
  if message.content.startswith("اقفللل"):
    if message.author.guild_permissions.administrator:
     
      
     channel = message.channel
     guild=message.guild
     permissions = channel.overwrites_for(guild.default_role)
     if permissions.send_messages is not False :
       
      
      await channel.set_permissions(guild.default_role,send_messages=False)
      await message.channel.send("اللواء قفل الشات ")
     else:
       await message.channel.send("طب م التشانل مقفوله يسطا")
    else:
      await message.channel.send("بس يا حبيبي كخه")
      
# =========================
#      فتح الشات بالكلام
# ========================= 
  if message.content.startswith("افتححح"):
    channel=message.channel
    guild=message.guild
    permissions = channel.overwrites_for(guild.default_role)
    if message.author.guild_permissions.administrator:
      if permissions.send_messages is False:
      
        
       await  channel.set_permissions(guild.default_role,send_messages=None)
       await message.channel.send("اللواء فتح الشات ")
      else:
        await message.channel.send("طب م التشانل مفتوحه")
    else:
      await message.channel.send("يا حبيبي بس")
      

        
  # =========================
  # شغل - تخزين البيانات
  # =========================

  if message.content == ("شغل"):
    if message.author.id in track_pepole:
      await message.channel.send("بيناتك متخزنة بالفعل")
      return

    wating = message.author
    await message.channel.send("ادخل سنك")
    return

  if wating == message.author:
    if message.content.isdigit():
      age = int(message.content)

      track_pepole[message.author.id] = {
        "name": message.author.name,
        "age": age
      }

      await message.channel.send("تم تخزين بياناتك")
      wating = None

    else:
      await message.channel.send("دخل سنك يا غبي")
      wating = None

    return

  # =========================
  # السجن
  # =========================

  if message.content.startswith("علسجننن") and message.mentions:
    if message.author.guild_permissions.administrator:

      member = message.mentions[0]

      if not can_moderate(message.author, member):
        await message.channel.send("أكبر الأول يا حبيبي 😂")
        return

      jail = message.guild.get_role(1545636378694520852)

      if jail not in member.roles:

        old_roles[member.id] = member.roles

        await member.edit(roles=[])

        await member.add_roles(jail)

        await message.channel.send(
          f"تمت اضافه رول {jail} الي العضو {member} وهو حاليا مسجون"
        )

      else:
        await message.channel.send("طب مهو مسجون يسطا")

    else:
      await message.channel.send("ماشي يسطا حاضر")

  # =========================
  # الإفراج
  # =========================

  if message.content.startswith("افراججج") and message.mentions:
    if message.author.guild_permissions.administrator:
      member = message.mentions[0]

      if not can_moderate(message.author, member):
        await message.channel.send("أكبر الأول يا حبيبي 😂")
        return

      jail = message.guild.get_role(1545636378694520852)
      if jail in member.roles:
        

       await member.remove_roles(jail)

       await member.edit(roles=old_roles[member.id])
       del old_roles[member.id]
      

       await message.channel.send(f"تم اعادة رولات العضو {member}")
      else:
        await message.channel.send("طب مهو مش مسجون يسطا")
    else:
      await message.channel.send("ماشي يسطا حاضر")
    
    

  
  
  # =========================
  # تايم اوت
  # =========================

  if message.content.startswith("اصصص") and message.mentions:
    if message.author.guild_permissions.moderate_members:

      member = message.mentions[0]

      if not can_moderate(message.author, member):
        await message.channel.send("أكبر الأول يا حبيبي 😂")
        return

      await member.timeout(timedelta(minutes=60))

      await message.channel.send("تم القمع")

    else:
      await message.channel.send("بس يا عبيط انت مش مود")

  # =========================
  # فك التايم اوت
  # =========================

  if message.content.startswith("فككك") and message.mentions:
    if message.author.guild_permissions.moderate_members:

      member = message.mentions[0]

      if not can_moderate(message.author, member):
        await message.channel.send("أكبر الأول يا حبيبي 😂")
        return

      await member.timeout(None)

      await message.channel.send("تم فك القمع")

    else:
      await message.channel.send("بس يا عبيط انت مش مود")

  # =========================
  # تست
  # =========================

  if message.content == "تست":
    await message.channel.send("شغال")

  
  await clint.process_commands(message)


# =========================
# Slash Commands
# =========================


#=================
#      kick
#=================

KICK_ROLE_ID = 1561820905053880471

kick_attempts = {}


@clint.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member):

    moderator = interaction.user

    if not any(role.id == KICK_ROLE_ID for role in moderator.roles):
        await interaction.response.send_message(
            "بس يا حبيبي",
            ephemeral=False
        )
        return

    user_id = moderator.id

    if user_id not in kick_attempts:
        kick_attempts[user_id] = 1

    if kick_attempts[user_id] <= 0:
        await interaction.response.send_message(
            "فرصك حاليًا 0، اطلب من الأدمنز يدوك محاولات.",
            ephemeral=False
        )
        return

    if not can_moderate(moderator, member):
        await interaction.response.send_message(
            "أكبر الأول يا حبيبي",
            ephemeral=False
        )
        return

    await member.kick()

    kick_attempts[user_id] -= 1

    await interaction.response.send_message(
        f"تم الطرد، متبقي لك {kick_attempts[user_id]} محاولة."
    )
    
    

@clint.tree.command(name="timeout")
@discord.app_commands.default_permissions(moderate_members=True)
async def timeout(
    interaction,
    member: discord.Member,
    duration: int,
    reason: str
):

  if not can_moderate(interaction.user, member):
    await interaction.response.send_message("أكبر الأول يا حبيبي ", ephemeral=False)
    return

  await member.timeout(
    timedelta(minutes=duration),
    reason=reason
  )

  await interaction.response.send_message(
    f"تايم اوت {duration} دقيقة بسبب {reason}"
  )


@clint.tree.command(name="untimeout")
@discord.app_commands.default_permissions(moderate_members=True)
async def untimeout(interaction, member: discord.Member):

  if not can_moderate(interaction.user, member):
    await interaction.response.send_message("أكبر الأول يا حبيبي 😂", ephemeral=True)
    return

  await member.timeout(None)

  await interaction.response.send_message(
    f"تم فك التايم اوت"
  )

#================
#      ban
#================

BAN_ROLE_ID = 1562058004076036227

ban_attempts = {}


@clint.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member):

    moderator = interaction.user

    if not any(role.id == BAN_ROLE_ID for role in moderator.roles):
        await interaction.response.send_message(
            "بس يا بابا",
            ephemeral=False
        )
        return

    user_id = moderator.id

    if user_id not in ban_attempts:
        ban_attempts[user_id] = 1

    if ban_attempts[user_id] <= 0:
        await interaction.response.send_message(
            "فرصك حاليًا 0، اطلب من الأدمنز يدوك محاولات.",
            ephemeral=False
        )
        return

    if not can_moderate(moderator, member):
        await interaction.response.send_message(
            "أكبر الأول يا حبيبي",
            ephemeral=False
        )
        return

    await member.ban()

    ban_attempts[user_id] -= 1

    await interaction.response.send_message(
        f"تم الحظر، متبقي لك {ban_attempts[user_id]} محاولة."
    )
    


# =========================
# Member Tracking
# =========================

@clint.tree.command(name="member_tracking")
@discord.app_commands.default_permissions(moderate_members=True)
async def member_tracking(interaction, member: discord.Member):

  if member.id in track_pepole:

    data = track_pepole[member.id]

    await interaction.response.send_message(
      f"الاسم :{data['name']}\n السن :{data['age']}"
    )

  else:

    await interaction.response.send_message(
      "غير مسجل في قاعدة البيانات"
    )
######################
#                    #
#        warn        #
#                    #
######################
@clint.tree.command(name="warn")
@discord.app_commands.default_permissions(moderate_members=True)
async def warn(interaction,member:discord.Member,reason:str):

  if not can_moderate(interaction.user, member):
    await interaction.response.send_message("أكبر الأول يا حبيبي 😂")
    return

  warn_count=warns[member.id]=warns.get(member.id,0)+1
  
  if warn_count == 3:
    await member.timeout(timedelta(minutes=10))
    await interaction.response.send_message(f"تم عمل تايم اوت  للعضو {member.mention} بسبب وصوله الي 3 تحذيرات")
    warns[member.id] = 0
  else:
    await interaction.response.send_message(f"تم إعطاء العضو {member.mention} تحذير بسبب {reason} وهذا التحذير رقم {warn_count}")
    

@clint.tree.command(name="my_warns")
async def my_warns(interaction,member:Optional[discord.Member] = None):

    if member is None:
        member = interaction.user

    if not interaction.user.guild_permissions.administrator:
        member = interaction.user

    my_warns = warns.get(member.id, 0)

    await interaction.response.send_message(
        f"العضو {member.mention} لديه {my_warns} تحذيرات"
    )
######################
#                    #
#        lock        #
#                    #
######################


@clint.tree.command(name="lock")
@discord.app_commands.default_permissions(manage_channels=True)
async def lock_chat(interaction):
    channel = interaction.channel

    await channel.set_permissions(
        interaction.guild.default_role,
        send_messages=False
    )

    await interaction.response.send_message("اللواء قفل الشات")
    
######################
#                    #
#       unlock       #
#                    #
######################


@clint.tree.command(name="unlock")
@discord.app_commands.default_permissions(manage_channels=True)
async def unlock_chat(interaction):
    channel = interaction.channel

    await channel.set_permissions(
        interaction.guild.default_role,
        send_messages=None
    )

    await interaction.response.send_message("اللواء فتح الشات")
##############
# my_messages
###############

@clint.tree.command(name="my_messages_level")
async def my_messages_Level(interaction, member: Optional[discord.Member] = None):
    if member is None:
        member = interaction.user

    user_data = exp_message.get(member.id, {})
    number = user_data.get("message", 0)
    Level = user_data.get("Level", 0)

    await interaction.response.send_message(
        f"العضو {member.mention} دي كل رسايله {number}\n# و لفله حاليا Level {Level}"
    )
#################
# delet_messages
#################


@clint.tree.command(name="clear", description="مسح عدد من الرسائل")
async def clear(interaction: discord.Interaction, amount: int):

    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "الأمر ده متاح داخل السيرفر بس.", ephemeral=True
        )
        return

    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "يا حبيبي 😂 معندكش صلاحية تستخدم الأمر ده!", ephemeral=True
        )
        return

    if not interaction.app_permissions.manage_messages:
        await interaction.response.send_message(
            "البوت معندوش صلاحية مسح الرسائل.", ephemeral=True
        )
        return

    if amount < 1 or amount > 500:
        await interaction.response.send_message(
            "اختار رقم من 1 لـ 500.", ephemeral=True
        )
        return

    channel = interaction.channel

    if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
        await interaction.response.send_message(
            "الأمر ده مش متاح في النوع ده من القنوات.", ephemeral=True
        )
        return

    await interaction.response.send_message("جاري فحص ومسح الرسائل...", ephemeral=True)

    try:
        # فحص تاريخ أقدم رسالة في النطاق المطلوب
        fourteen_days_ago = discord.utils.utcnow() - datetime.timedelta(days=14)
        
        # جلب الرسائل للتأكد من تاريخها
        messages = [message async for message in channel.history(limit=amount)]
        
        if messages:
            oldest_message = messages[-1] # أقدم رسالة في اللستة
            if oldest_message.created_at < fourteen_days_ago:
                await channel.send("تاريخ الرسائل دي أو بعضها أكتر من 14 يوم، مش هعرف أمسحها بسبب قيود ديسكورد!")
                return

        # مسح الرسائل إذا كانت أحدث من 14 يوم
        deleted = await channel.purge(limit=amount)
        await channel.send(f"تم مسح {len(deleted)} رسالة بنجاح 🧹")

    except discord.Forbidden:
        await channel.send("البوت معندوش الصلاحيات الكافية لمسح الرسائل في هذه القناة.")

    except discord.HTTPException as error:
        print(f"Clear error: {error}")
        await channel.send("حصل خطأ أثناء مسح الرسائل (غالباً بسبب وجود رسائل أقدم من 14 يوم).")
###############
#زيادة محاولات الكيك 
###############
@clint.tree.command(name="زيادة_محاولات_الكيك")
@discord.app_commands.default_permissions(administrator=True)
async def add_kick_attempts(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):
    if amount <= 0:
        await interaction.response.send_message(
            "لازم عدد المحاولات يكون أكبر من صفر.",
            ephemeral=False
        )
        return

    if not any(role.id == KICK_ROLE_ID for role in member.roles):
        await interaction.response.send_message(
            "العضو ده مش معاه رول الكيك.",
            ephemeral=False
        )
        return

    user_id = member.id

    if user_id not in kick_attempts:
        kick_attempts[user_id] = 1

    kick_attempts[user_id] += amount

    await interaction.response.send_message(
        f"تم إضافة {amount} محاولات للكيك لـ {member.mention}.\n"
        f"إجمالي محاولاته حاليًا: {kick_attempts[user_id]}."
    )
##############
#زيادة محاولات البان
##############
@clint.tree.command(name="زيادة_محاولات_البان")
@discord.app_commands.default_permissions(administrator=True)
async def add_ban_attempts(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):
    if amount <= 0:
        await interaction.response.send_message(
            "لازم عدد المحاولات يكون أكبر من صفر.",
            ephemeral=False
        )
        return

    if not any(role.id == BAN_ROLE_ID for role in member.roles):
        await interaction.response.send_message(
            "العضو ده مش معاه رول البان.",
            ephemeral=False
        )
        return

    user_id = member.id

    if user_id not in ban_attempts:
        ban_attempts[user_id] = 1

    ban_attempts[user_id] += amount

    await interaction.response.send_message(
        f"تم إضافة {amount} محاولات للبان لـ {member.mention}.\n"
        f"إجمالي محاولاته حاليًا: {ban_attempts[user_id]}."
    )
##############
#عرض محاولات كيك
###############
@clint.tree.command(name="محاولاتي_كيك")
async def my_kick_attempts(interaction: discord.Interaction):

    moderator = interaction.user

    if not any(role.id == KICK_ROLE_ID for role in moderator.roles):
        await interaction.response.send_message(
            "الأمر ده مخصص للي معاهم رول الكيك.",
            ephemeral=False
        )
        return

    user_id = moderator.id
    attempts = kick_attempts.get(user_id, 1)

    await interaction.response.send_message(
        f"معاك {attempts} محاولة كيك حاليًا."
    )
################
# عرض محاولات بان
################
@clint.tree.command(name="محاولاتي_بان")
async def my_ban_attempts(interaction: discord.Interaction):

    moderator = interaction.user

    if not any(role.id == BAN_ROLE_ID for role in moderator.roles):
        await interaction.response.send_message(
            "الأمر ده مخصص للي معاهم رول البان.",
            ephemeral=False
        )
        return

    user_id = moderator.id
    attempts = ban_attempts.get(user_id, 1)

    await interaction.response.send_message(
        f"معاك {attempts} محاولة بان حاليًا."
    )
###############
# تصفير الكيك
###############
@clint.tree.command(name="تصفير_محاولات_الكيك")
@discord.app_commands.default_permissions(administrator=True)
async def reset_kick_attempts(
    interaction: discord.Interaction,
    member: discord.Member
):
    if not any(role.id == KICK_ROLE_ID for role in member.roles):
        await interaction.response.send_message(
            "العضو ده مش معاه رول الكيك.",
            ephemeral=False
        )
        return

    kick_attempts[member.id] = 0

    await interaction.response.send_message(
        f"تم تصفير محاولات الكيك للعضو {member.mention}."
    )
###################
#تصفير البان 
###################
@clint.tree.command(name="تصفير_محاولات_البان")
@discord.app_commands.default_permissions(administrator=True)
async def reset_ban_attempts(
    interaction: discord.Interaction,
    member: discord.Member
):
    if not any(role.id == BAN_ROLE_ID for role in member.roles):
        await interaction.response.send_message(
            "العضو ده مش معاه رول البان.",
            ephemeral=False
        )
        return

    ban_attempts[member.id] = 0

    await interaction.response.send_message(
        f"تم تصفير محاولات البان للعضو {member.mention}."
    )
##############
# نظام كشف الاسبام
############## 

# إعدادات نظام Anti-Spam
SPAM_WINDOW = 3
SPAM_LIMIT = 5
DUPLICATE_LIMIT = 3
TIMEOUT_DURATION = 7200

# تخزين أوقات الرسائل لكل عضو
message_history = defaultdict(deque)


@clint.listen("on_message")
async def anti_spam(message: discord.Message):

    # تجاهل رسائل البوتات والرسائل الخاصة
    if message.author.bot or message.guild is None:
        return

    # جلب العضو من السيرفر
    member = message.guild.get_member(message.author.id)

    if member is None:
        return

    # استثناء الأدمنز
    if member.guild_permissions.administrator:
        return

    user_id = member.id
    now = time.monotonic()

    history = message_history[user_id]

    # حذف الرسائل الأقدم من 3 ثوانٍ
    while history and now - history[0][0] > SPAM_WINDOW:
        history.popleft()

    # تسجيل الرسالة الحالية
    content = message.content.strip().casefold()
    history.append((now, content))

    # فحص سرعة إرسال الرسائل
    too_fast = len(history) >= SPAM_LIMIT

    # فحص تكرار نفس الرسالة
    duplicate_count = sum(
        1 for _, old_content in history
        if content and old_content == content
    )

    repeated = duplicate_count >= DUPLICATE_LIMIT

    # الخروج لو مفيش Spam
    if not too_fast and not repeated:
        return

    # تنظيف سجل العضو
    message_history.pop(user_id, None)

    try:
        await member.timeout(
            timedelta(seconds=TIMEOUT_DURATION),
            reason="Anti-Spam: Excessive or repeated messages"
        )

        await message.channel.send(
            f"🚨 **Anti-Spam**\n"
            f"العضو: {member.mention}\n"
            f"السبب: إرسال رسائل بسرعة أو تكرارها.\n"
            f"العقوبة: Timeout لمدة ساعتين."
        )

    except discord.Forbidden:
        await message.channel.send(
            f"⚠️ لم أستطع إعطاء Timeout لـ {member.mention}.\n"
            "تأكد أن عندي صلاحية Moderate Members "
            "وأن رتبة البوت أعلى من رتبة العضو."
        )

    except discord.HTTPException:
        await message.channel.send(
            f"❌ حصل خطأ أثناء محاولة إعطاء Timeout لـ {member.mention}."
        )
        


        
    
clint.run(TOKEN)