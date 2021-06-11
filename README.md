## Installation

Developed and tested in
```sh
Python 3.7.4
```

Install dependencies
```
pip install -r requirements.txt
```

## Spotify Security

1. Register as a developer in Spotify to get access to the API.

**Valuable output:** `client_id` and `client_secret`

2. The first step in the security flow is to get the authorization from the user (in this case ourselves) so that an external application (in this case the code in this repository) can access the Spotify API of the user. The authorization is done via a GET request asking for certain privileges. This request must be done using a web browser since it will have a redirect to a specified URL.

`GET https://accounts.spotify.com/authorize`

Query parameters:
- `client_id`: Value obtained in the last step.
- `response_type`: Set to `code`
- `redirect_uri`: When the user accepts to give the privileges (specified in `scope`) Spotify will redirect to this specified URL. The redirect URL will have **valuable output** that we will use in the next steps. I used the URL for this repo to redirect: https://github.com/aponcedeleonch/fetch_spotify.
- `scope`: The list of permissions that we are asking for the user. A list with all the scopes and its description can be found [here](https://developer.spotify.com/documentation/general/guides/scopes/). The scopes I asked to make the code in this repository work are:
    - playlist-modify-private
    - playlist-modify-public
    - playlist-read-private
    - playlist-read-collaborative
    - user-library-read
    - user-modify-playback-state
    - user-read-playback-state

Example:

I copy pasted the following in a web browser:

```
https://accounts.spotify.com/authorize?client_id=<my_client_id>&response_type=code&redirect_uri=https://github.com/aponcedeleonch/fetch_spotify&scope=playlist-modify-private%20playlist-modify-public%20playlist-read-private%20playlist-read-collaborative%20user-library-read%20user-modify-playback-state%20user-read-playback-state
```

*Note:* I used Postman to format the URL above.

**Valuable output:** `user_code`

3. Now we can exchange the obtained `user_code` in the last step for a token to make requests to the Spotify API. The functions for this exchange is already implemented in the code of this repository in the file `spotify_api.py`.
