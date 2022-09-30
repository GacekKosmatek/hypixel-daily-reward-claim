from typing import Dict, List, Union
from dataclasses import dataclass
import requests
import json
import re

appdata_regex = re.compile(r"window\.appData = '(.+)';")
csrf_token_regex = re.compile(r"window\.securityToken = \"(.+)\";")
reward_id_regex = re.compile(r"(https?://)?rewards.hypixel.net/claim-reward/(.{8})/?")
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}
@dataclass(frozen=True)
class Reward:
    rarity: str
    reward_type: str
    amount: int
    game: str
    package: str
    reward_id: int = None


def get_rewards(page_string: str) -> List[Reward]:
    if js_list := appdata_regex.findall(page_string):
        js: dict = json.loads(js_list[0])
    else:
        print(page_string)
        raise RuntimeError("Could not find App Data string")
    if not js.get("rewards"):
        raise RuntimeError("Could not get rewards from string")
    rewards = []
    for index, reward in enumerate(js["rewards"]):
        reward: Dict[str, Union[str, int]]
        rewards.append(
            Reward(
                normalize_string_if_not_none(reward['rarity']),
                normalize_string_if_not_none(reward['reward']),
                normalize_string_if_not_none(reward.get('amount', 1)),
                normalize_string_if_not_none(reward.get('gameType')),
                normalize_string_if_not_none(reward.get("package")),
                index
            )
        )
    return rewards

def get_csrf_token(page_string: str) -> str:
    if csrf_token := csrf_token_regex.findall(page_string):
        return csrf_token[0]
    raise RuntimeError("Could not find CSRF token string")

def claim_reward(reward: Reward, url: str, csrf_token: str, csrf_cookie: str):
    reward_id_list = reward_id_regex.findall(url)
    try:
        reward_id = reward_id_list[0][1]
    except IndexError as e:
        raise RuntimeError("Could not find reward ID") from e
    r = requests.post("https://rewards.hypixel.net/claim-reward/claim", params={
        "option": reward.reward_id,
        "id": reward_id,
        "activeAd": 1,
        "_csrf": csrf_token,
        "watchedFallback": "false",
    }, cookies={"_csrf": csrf_cookie}, headers=headers)
    if (r.text != "reward claimed"):
        raise RuntimeError("Failed to claim reward")

def concat_if_not_none(*args: List[str]):
    return " ".join(arg for arg in args if arg is not None)

def normalize_string_if_not_none(string: str):
    if string is None:
        return None
    elif isinstance(string, str):
        return string.replace('_', ' ').capitalize()
    else:
        return string

if __name__ == "__main__":
    url = input("URL > ")
    r = session.get(url, headers=headers)
    rewards = get_rewards(r.text)
    csrf_token = get_csrf_token(r.text)
    for index, i in enumerate(rewards, start=1):
        print(f"{index}. [{i.rarity}] {i.amount}x {concat_if_not_none(i.game, i.package, i.reward_type)}")
    reward_id = int(input("Reward > ")) - 1 # We subtract 1 to get a index in the list
    try: claim_reward(rewards[reward_id], url, csrf_token, r.cookies["_csrf"])
    except Exception: pass
    print("Successfully claimed!")
