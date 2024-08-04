import nextcord, config, datetime, json, re, httpx, certifi
from nextcord.ext import commands

bot = commands.Bot(
    command_prefix='nyx!',
    help_command=None,
    intents=nextcord.Intents.all(),
    strip_after_prefix=True,
    case_insensitive=True
)

class topupModal(nextcord.ui.Modal):

    def __init__(self):
        super().__init__(title='🧧เติมเงิน', timeout=None, custom_id='topup-modal')
        self.link = nextcord.ui.TextInput(
            label = '🧧 เติมเงินเข้าระบบ',
            placeholder = 'วางลิ้งอังเปาตรงนี้ !',
            style = nextcord.TextInputStyle.short,
            required = True
        )
        self.add_item(self.link)

    async def callback(self, interaction: nextcord.Interaction):
        link = str(self.link.value).replace(' ', '')
        message = await interaction.response.send_message(content='checking.', ephemeral=True)
        if re.match(r'https:\/\/gift\.truemoney\.com\/campaign\/\?v=+[a-zA-Z0-9]{18}', link):
            voucher_hash = link.split('?v=')[1]
            response = httpx.post(
                url = f'https://gift.truemoney.com/campaign/vouchers/{voucher_hash}/redeem',
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/8a0.0.3987.149 Safari/537.36'
                },
                json = {
                    'mobile': config.phoneNumber,
                    'voucher_hash': f'{voucher_hash}'
                },
                verify=certifi.where(),
            )
            if (response.status_code == 200 and response.json()['status']['code'] == 'SUCCESS'):
                data = response.json()
                amount = int(float(data['data']['my_ticket']['amount_baht']))
                userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
                if (str(interaction.user.id) not in userJSON):
                    userJSON[str(interaction.user.id)] = {
                        "userId": interaction.user.id,
                        "point": amount,
                        "all-point": amount,
                        "transaction": [
                            {
                                "topup": {
                                    "url": link,
                                    "amount": amount,
                                    "time": str(datetime.datetime.now())
                                }
                            }
                        ]
                    }
                else:
                    userJSON[str(interaction.user.id)]['point'] += amount
                    userJSON[str(interaction.user.id)]['all-point'] += amount
                    userJSON[str(interaction.user.id)]['transaction'].append({
                        "topup": {
                            "url": link,
                            "amount": amount,
                            "time": str(datetime.datetime.now())
                        }
                    })
                json.dump(userJSON, open('./database/users.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
                embed = nextcord.Embed(description='เติมเงินสำเร็จ', color=nextcord.Color.green())
            else:
                embed = nextcord.Embed(description='เติมเงินไม่สำเร็จ', color=nextcord.Color.red())
        else:
            embed = nextcord.Embed(description='รูปแบบลิ้งค์ไม่ถูกต้อง', color=nextcord.Color.red())
        await message.edit(content=None,embed=embed)

class sellroleView(nextcord.ui.View):

    def __init__(self, message: nextcord.Message, value: str):
        super().__init__(timeout=None)
        self.message = message
        self.value = value

    @nextcord.ui.button(
        label='ยีนยัน',
        custom_id='already',
        style=nextcord.ButtonStyle.green,
        row=1
    )
    async def already(self, button: nextcord.Button, interaction: nextcord.Interaction):
        roleJSON = json.load(open('./database/roles.json', 'r', encoding='utf-8'))
        userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
        if (str(interaction.user.id) not in userJSON):
            embed = nextcord.Embed(description='เติมเงินเพื่อเปิดบัญชี', color=nextcord.Color.red())
        else:
            if (userJSON[str(interaction.user.id)]['point'] >= roleJSON[self.value]['price']):
                userJSON[str(interaction.user.id)]['point'] -= roleJSON[self.value]['price']
                userJSON[str(interaction.user.id)]['transaction'].append({
                    "payment": {
                        "roleId": self.value,
                        "time": str(datetime.datetime.now())
                    }
                })
                json.dump(userJSON, open('./database/users.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
                if ('package' in self.value):
                    for roleId in roleJSON[self.value]['roleIds']:
                        try:
                            await interaction.user.add_roles(nextcord.utils.get(interaction.user.guild.roles, id = roleId))
                        except:
                            pass
                    embed = nextcord.Embed(description=f'ซื้อยศสำเร็จ ได้รับ PACKAGE <@&{roleJSON[self.value]["name"]}>', color=nextcord.Color.red())
                else:
                    embed = nextcord.Embed(description=f'ซื้อยศสำเร็จ ได่รับยศ <@&{roleJSON[self.value]["roleId"]}>', color=nextcord.Color.red())
                    await interaction.user.add_roles(nextcord.utils.get(interaction.user.guild.roles, id = roleJSON[self.value]['roleId']))
            else:
                embed = nextcord.Embed(description=f'เงินของท่านไม่เพียงพอ ขาดอีด ({roleJSON[self.value]["price"] - userJSON[str(interaction.user.id)]["point"]})', color=nextcord.Color.red())
        return await self.message.edit(embed=embed, view=None, content=None)

    @nextcord.ui.button(
        label='ยกเลิก',
        custom_id='cancel',
        style=nextcord.ButtonStyle.red,
        row=1
    )
    async def cancel(self, button: nextcord.Button, interaction: nextcord.Interaction):
        return await self.message.edit(content='ยกเลิกสำเร็จ',embed=None, view=None)

class sellroleSelect(nextcord.ui.Select):

    def __init__(self):
        options = []
        roleJSON = json.load(open('./database/roles.json', 'r', encoding='utf-8'))
        for role in roleJSON:
            options.append(nextcord.SelectOption(
                label=roleJSON[role]['name'],
                description=roleJSON[role]['description'],
                value=role,
                emoji=roleJSON[role]['emoji']
            ))
        super().__init__(
            custom_id='select-role',
            placeholder='🎁เลือกยศที่คุณต้องการซื้อ',
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )

    async def callback(self, interaction: nextcord.Interaction):
        message = await interaction.response.send_message(content='กำลังดำเนินการ', ephemeral=True)
        selected = self.values[0]
        if ('package' in selected):
            roleJSON = json.load(open('./database/roles.json', 'r', encoding='utf-8'))
            embed = nextcord.Embed()
            embed.description = f'''
**คุณแน่ใจหรือไม่ที่จะซื้อ PACKAGE {roleJSON[selected]['name']}**
'''
            await message.edit(content=None,embed=embed,view=sellroleView(message=message, value=selected))
        else:
            roleJSON = json.load(open('./database/roles.json', 'r', encoding='utf-8'))
            embed = nextcord.Embed()
            embed.description = f'''
**คุณแน่ใจหรือไม่ที่จะซื้อยศ** <@&{roleJSON[selected]['roleId']}>
'''
            await message.edit(content=None,embed=embed,view=sellroleView(message=message, value=selected))

class setupView(nextcord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(sellroleSelect())

    @nextcord.ui.button(
        label='🧧เติมเงิน',
        custom_id='topup',
        style=nextcord.ButtonStyle.red,
        row=1
    )
    async def topup(self, button: nextcord.Button, interaction: nextcord.Interaction):
        await interaction.response.send_modal(topupModal())

    @nextcord.ui.button(
        label='📘เช็คเงิน',
        custom_id='balance',
        style=nextcord.ButtonStyle.red,
        row=1
    )
    async def balance(self, button: nextcord.Button, interaction: nextcord.Interaction):
        userJSON = json.load(open('./database/users.json', 'r', encoding='utf-8'))
        if (str(interaction.user.id) not in userJSON):
            embed = nextcord.Embed(description='เติมเงินเพื่อเปิดบัญชี', color=nextcord.Color.red())
        else:
            embed = nextcord.Embed(description=f'ยอดเงินคงเหลือ {userJSON[str(interaction.user.id)]["point"]}', color=nextcord.Color.green())
        return await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(setupView())
    print(f'ชื่อบอทคือ {bot.user}')

@bot.slash_command(name='setup-buy-role',description='setup')
async def setup(interaction: nextcord.Interaction):
    if (interaction.user.id not in config.ownerIds):
        return await interaction.response.send_message(content='[ERROR] No Permission For Use This Command.', ephemeral=True)
    embed = nextcord.Embed()
    embed.description = f'''
```
・ 🧧﹒บอทซื้อยศ 24 ชั่วโมง
・ 💳﹒เติมเงินด้วยระบบอั่งเปา
・ ✨﹒ระบบออโต้ 24 ชั่วโมง
・ 💲﹒ซื้อแล้วได้ยศเลย
・ 🔓﹒เติมเงินเพื่อเปิดบัญชี 
```
'''
    embed.color = nextcord.Color.re()
    embed.set_image(url='https://i.pinimg.com/originals/0e/c3/e4/0ec3e4be8567cab86dd4c3300f8dcad3.jpg')
    await interaction.channel.send(embed=embed, view=setupView())
    await interaction.response.send_message(content='[SUCCESS] Done.', ephemeral=True)

@bot.slash_command(
    name='add-role',
    description='add role',
    guild_ids=[config.serverId]
)
async def addrole(interaction: nextcord.Interaction, role: nextcord.Role, price: int):
    if (interaction.user.id not in config.ownerIds):
        return await interaction.response.send_message(content='[ERROR] No Permission For Use This Command.', ephemeral=True)
    roleJSON = json.load(open('./database/roles.json', 'r', encoding='utf-8'))
    roleJSON[str(role.id)] = {
        "name": role.name,
        "description": f"{role.name} ราคา {price}",
        "price": price,
        "roleId": role.id,
        "add-by": interaction.user.id,
        "add-time": str(datetime.datetime.now()),
        "emoji": "<a:1064517829983993967:1161936578734727199>"
    }
    json.dump(roleJSON, open('./database/roles.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
    await interaction.response.send_message(content='[SUCCESS] Done.', ephemeral=True)

@bot.slash_command(
    name='del-role',
    description='del role',
    guild_ids=[config.serverId]
)
async def delrole(interaction: nextcord.Interaction, role: nextcord.Role):
    if (interaction.user.id not in config.ownerIds):
        return await interaction.response.send_message(content='[ERROR] No Permission For Use This Command.', ephemeral=True)
    roleJSON = json.load(open('./database/roles.json', 'r', encoding='utf-8'))
    del roleJSON[str(role.id)]
    json.dump(roleJSON, open('./database/roles.json', 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
    await interaction.response.send_message(content='[SUCCESS] Done.', ephemeral=True)


bot.run(config.botToken)