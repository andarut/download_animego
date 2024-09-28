# ⚙️ download_animego

Script to download any anime from https://animego.org/

# Demo

```bash
./demo.sh
```

**give it time, because timeouts are placed for old hardware**

it will download Kabaneri

## Features

- auto handling titles (if title not found, you can type it like in demo)
- auto vpn (using `vpn_on.sh` and `vpn_off.sh` scripts and Wireguard config you can give selenium vpn permissions)
- select audio track (whatever you like)
- no lost progress, to can shut if off and continue without losing progress in downloading

## Message for animego

**Your website is great and i want to give people possibility to download anime and watch it offline.**

Throught my code you will see how i managed to download from your website. **To be short and polity i explain "hack" steps by steps:**

1. Check main page (get title and episodes count)
2. Wait seconds after all ads and get `base_url` - part of all chunks urls
3. Download chunks. You store them as `m4s` files which a basically `mp4`. There is no way to check what number of chunks are there, so i download it until i get empty chunk (it's size is `548`). Of course process same for audio and video chunks.
4. Concat chunks together. Simple cat all `m4s` files and as a result i get working `mp4` file.

If you modify you storage system i will continue to modifing this script, because i want to watch anime offline without your ads. Anyway i think you don't give a fuck about this script, so i just wanna tell you that i am not using it in wrong way, just for myself.
