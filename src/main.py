import json
import aiohttp
import requests
import os
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw 
import operator
from flask import Flask, request, render_template, send_from_directory

app = Flask('decks')

players = {}

TOKEN = "" # A clash royale dev token with 128.128.128.128 whitelisted for dynamic IP usage

async def getClan(name):
    url = f"https://proxy.royaleapi.dev/v1/clans?name={name}"

    payload = "%7B%20%22payload%22=%22%22%2C%20%22signature%22%3A%20%22%22%20%7D"
    headers = {
        'content-type': "application/json",
        'authorization': f"Bearer {TOKEN}",
        }
    
    async with aiohttp.ClientSession() as client:
      async with client.get(url=url, headers=headers, data=payload) as r:
        data = await r.json()

    tag = data['items'][0]['tag']
    tag = tag[1:]
    
    url = f"https://proxy.royaleapi.dev/v1/clans/%23{tag}/members"

    payload = "%7B%20%22payload%22=%22%22%2C%20%22signature%22%3A%20%22%22%20%7D"
    headers = {
        'content-type': "application/json",
        'authorization': f"Bearer {TOKEN}",
        }

    async with aiohttp.ClientSession() as client:
      async with client.get(url=url, headers=headers, data=payload) as r:
        m = await r.json()

    members = m['items']
    items = []
    for i in members:
      clan_member = {}
      clan_member['name'] = i['name']
      clan_member['tag'] = i['tag']

      items.append(clan_member)
    clan_data = {}
    clan_data['name'] = data['items'][0]['name']
    clan_data['members'] = items
    
    return clan_data


async def getPlayerCards(PlayerTag):
      try:
        TAG = PlayerTag[1:]

        url = f"https://proxy.royaleapi.dev/v1/players/%23{TAG}"

        payload = "%7B%20%22payload%22=%22%22%2C%20%22signature%22%3A%20%22%22%20%7D"
        headers = {
            'content-type': "application/json",
            'authorization': f"Bearer {TOKEN}",
            }

        async with aiohttp.ClientSession() as client:
          async with client.get(url=url, headers=headers, data=payload) as r:
            data = await r.json()

        deck_raw = data['currentDeck']

        player = {}
        player['name'] = data['name']
        deck = []

        for card in deck_raw:
            c = {}
            levelAdd = 13-card['maxLevel']
            c['name'] = card['name']
            c['level'] = card['level'] + levelAdd
            c['icon'] = card['iconUrls']['medium']
            c['id'] = str(card['id'])
            
            deck.append(c)

        deckLink = "https://link.clashroyale.com/deck/en?deck="
        for i in range(len(deck)-1):
            card = deck[i]
            deckLink += card['id'] + ";"
        deckLink+=deck[len(deck)-1]['id']

        player['deck_link'] = deckLink
        player['deck'] = deck

        players[data['name'].lower()] = data['tag']

        return player
      except:
        return None


def makeImage(data):
    font = ImageFont.truetype("./fonts/YouBlockhead.ttf", 20)
    size = (555,400)

    itemX = 0
    itemY = 10

    
    img = Image.new('RGB', size, color = (22, 112, 222))

    draw = draw = ImageDraw.Draw(img)

    count = 0

    for card in data['deck']:
        url = card['icon']
        icon = Image.open(requests.get(url, stream=True).raw)
        icon = icon.resize((round(icon.width/2), round(icon.height/2)))

        img.paste(icon, (itemX, itemY),icon)
        draw.text((itemX+(round(icon.width/2)-10),itemY+icon.height-5), str(card['level']), fill="white", font=font)
        itemX+=icon.width
        count+=1
        if(count>=4):
            count = 0
            itemX=0
            itemY+=icon.height+25
    
    return img

@app.route('/')
def home():
  return render_template('home.html')

@app.route('/clan_search', methods =["GET", "POST"])
async def clans():
  if request.method == "POST":
    clan = request.form.get("clan")
    clan_data = await getClan(clan)
    if(clan_data):
      clan_name = clan_data['name']
      members = clan_data['members']
      members.sort(key=operator.itemgetter('name'))
      count=len(members)
      return render_template('clans.html', names=members, clan_name=clan_name, count=count)
    else:
      return "Clan not found"


@app.route('/player_search', methods =["GET", "POST"])
async def index():
  if request.method == "POST":
    player = request.form.get("name")
    if("#" in player):
      data = await getPlayerCards(player)
    elif(player.lower() in players.keys()):
      data = await getPlayerCards(players[player])
    else:
      return "Player not found, use their tag (#)"
    if(data):
      img = makeImage(data)
      img.save(f"./templates/deck.jpg", "JPEG", quality = 100)

      name = data['name']
      link = data['deck_link']

      return render_template('index.html', name=name, link=link)
    else:
      return "Player not found"

@app.route('/player', methods=['GET'])
async def tag():
  if("tag" in request.args):
    id = str(request.args["tag"])
    tag = "#" + id
    data = await getPlayerCards(tag)
    if(data):
        img = makeImage(data)
        img.save(f"./templates/deck.jpg", "JPEG", quality = 100)

        name = data['name']
        link = data['deck_link']

        return render_template('index.html', name=name, link=link)
    else:
      return "Player not found"
  else:
    return "Player not found"
    

@app.route('/image/<path:path>')
def send_templates(path):
    return send_from_directory('templates/', path)

if __name__ == '__main__':
  app.run(
    host='0.0.0.0',
    port="8888"
  )
