# Spotify helper

I began this project in my free time because of two main reasons:
1. I thought Spotify was magically deleting the saved songs in my library since there were some songs that I remembered adding but I have never heard.
2. I was tired of Spotify shuffle. I felt I always ended up listening to the same songs over and over again.

The two above reasons were driving me crazy since I always put my Spotify saved songs in shuffle when I go out for a run. On a good Sunday I run around  36km, for about 3 hours, which means Spotify driving me crazy for 2 hours and 55 minutes. One day I decided enough is enough and said "What the heck! I know how to program. Spotify surely has an API so that I can at least make sure my songs are not disappearing into thin air".

The above story just to justify the limited but enough functionalities (for me) that this script has:
- **Download saved songs**: Just what it sounds like. Gets the metadata of the saved songs from my library.
- **Compare saved songs**: This functionality solves directly reason number 1 for creating this project. It makes a diff of the last saved songs and the current saved songs in my Library. For this to work obviously the download functionality needs to be used at least once before.
- **Get recently played songs**: Again, it does just what it says. It gets from Spotify history the most recent played songs. This is more of a helper functionality for the next one.
- **Play saved songs**: It sends to the queue, in a random order, a certain number of songs from my Library. With this I take care of reason number 2. The random order is something that I programmed so that at least this time, if I have some complain with the shuffle, I could take care of it.

Were there some other random Spotify players already out there? Probably. Could this be done easier without any programming? Maybe. But now I have the control on the order I listen to my Spotify songs and I can change it at any given time plus I had fun programming.

## Usage

Before trying to use the script take a look at the [Requirements section](#requirements)

### Download saved songs

```sh
python spotify_helper.py -a download_saved_songs
```

### Compare saved songs

```sh
python spotify_helper.py -a compare_saved_songs
```

### Get recently played songs

```sh
python spotify_helper.py -a get_recently_played_songs
```

### Play saved songs

By default the script will try to send to the queue 100 songs with the following command:
```sh
python spotify_helper.py -a play_saved_songs
```

You can adjust the number of songs you want to send to the queue with the parameter. `--num_play_songs`, e.g.
```sh
python spotify_helper.py -a play_saved_songs --num_play_songs 10
```

The script will query every 5 minutes Spotify trying to get the recently played songs. This is done to keep track of the songs that are actually played. If a song was played then such song will have a minor probability to get played again in the future i.e. the script will send to the queue the songs that have played the least amount of times in your Library. To modify the frequency at which the scripts queries Spotify use the parameter `--sleep_time`.
```sh
python spotify_helper.py -a play_saved_songs --num_play_songs 10 --sleep_time 1
```

If you want to supress completely the waiting for a song to be played:
```sh
python spotify_helper.py -a play_saved_songs --num_play_songs 10 --not_wait_songs_to_play
```

Finally, to get some general usage of the script use:
```sh
python spotify_helper.py -h
```

## Requirements

To run and use the script installation-wise basically the only thing you need is Python and the library `requests`. Check out [Installation section](#installation).

Unfortunately, this script does not work right out of the box. Some manual steps have to be peformed to get the Spotify credentials. You will need to get your own developer credentials and follow some steps indicated in the [Spotify security section](#spotify-security). Once you have completed the steps you will need to create a JSON file called `spotify_env.json` with the obtained credentials. The format of the JSON file is the following.
```JSON
{
  "user_code": "<your-user_code>",
  "redirect_uri": "<your-redirect_uri>",
  "client_id": "<your-client_id>",
  "client_secret": "<your-client_secret>",
}
```

You can change the name of the JSON file from `spotify_env.json` to whatever you want but the script will look by default for that file. You can specify your own JSON file with the option `--spotify_env_file` of the script.

### Installation

Developed and tested in
```sh
Python 3.7.4
```

Install dependencies
```
pip install -r requirements.txt
```

### Spotify Security

1. Register as a developer in Spotify to get access to the API. Register [here](https://developer.spotify.com/dashboard/).

**Valuable output:** `client_id` and `client_secret`

2. The first step in the security flow is to get the authorization from the user (in this case ourselves) so that an external application (in this case the code in this repository) can access the Spotify API of the user. The authorization is done via a GET request asking for certain privileges. This request must be done using a web browser since it will have a redirect to a specified URL.

`GET https://accounts.spotify.com/authorize`

Query parameters:
- `client_id`: Value obtained in the last step.
- `response_type`: Set to `code`
- `redirect_uri`: When the user accepts to give the privileges (specified in `scope`) Spotify will redirect to this specified URL. The redirect URL will have **valuable output** that we will use in the next steps. I used the URL for this repository as `redirect_uri`: https://github.com/aponcedeleonch/fetch_spotify.
- `scope`: The list of permissions that we are asking for the user. A list with all the scopes and its description can be found [here](https://developer.spotify.com/documentation/general/guides/scopes/). The scopes I asked to make the code in this repository work are:
    - playlist-modify-private
    - playlist-modify-public
    - playlist-read-private
    - playlist-read-collaborative
    - user-library-read
    - user-modify-playback-state
    - user-read-playback-state

Example:

I copy-pasted the following in a web browser:

> ```https://accounts.spotify.com/authorize?client_id=<my_client_id>&response_type=code&redirect_uri=https://github.com/aponcedeleonch/fetch_spotify&scope=playlist-modify-private%20playlist-modify-public%20playlist-read-private%20playlist-read-collaborative%20user-library-read%20user-modify-playback-state%20user-read-playback-state```

*Note:* I used Postman to format the URL above.

**Valuable output:** `user_code`

General instructions from Spotify: https://developer.spotify.com/documentation/general/guides/authorization-guide/

3. Now we can exchange the obtained `user_code` in the last step for a token to make requests to the Spotify API. The functions for this exchange is already implemented in the code of this repository in the file `spotify_api.py`. Now you can put all the **Valuable output** you obtained in a JSON file and run the available commands of the script. The format of the JSON file is specified at the [Requirements section](#requirements)
