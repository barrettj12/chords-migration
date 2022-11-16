# https://gkeepapi.readthedocs.io/en/latest/

import discogs_client
from fuzzywuzzy import process
import gkeepapi
import json
import keyring
import os
import string
from titlecase import titlecase

# fill these in
EMAIL = ''
PASSWORD = ''
DISCOGS_TOKEN = ''

# [artist, album] -> []song
trackLists = {}

def ensureLogin(keep):
    try:
        print('trying to reuse token')
        token = keyring.get_password('google-keep-token', EMAIL)
        keep.resume(EMAIL, token)
    except Exception as e:
        print('token retrieval failed')
        print(e)
        # Need to get new token
        print('logging in again for new token')
        keep.login(EMAIL, PASSWORD)
        token = keep.getMasterToken()
        keyring.set_password('google-keep-token', EMAIL, token)
    print('Got token :)', end='\n\n')


# setup apis
keep = gkeepapi.Keep()
ensureLogin(keep)
d = discogs_client.Client('barrettj12ChordParser/0.1', user_token=DISCOGS_TOKEN)
notes = keep.find(labels=[keep.findLabel('Chords')])


# main loop
def main():
    for note in notes:
        artist, songOrAlbum = parseTitle(note.title)
        if '***' in note.text:
            album = songOrAlbum
            spl = note.text.split('***')
            for i in range(1, len(spl), 2):
                song = titlecase(spl[i].strip())
                artist, album = maybeWriteMeta(artist, song, album)
                maybeWriteChords(song, spl[i+1])
        else:
            song = songOrAlbum
            maybeWriteMeta(artist, song, '')
            maybeWriteChords(song, note.text)


# helper functions
def parseTitle(title):
    spl = title.split(' - ', 1)
    if len(spl) > 1:
        return spl[0].strip(), spl[1].strip()
    else:
        return "", spl[0].strip()

def maybeWriteMeta(artist, song, album):
    id = getID(song)
    try:
        f = openFile(f'./data/{id}', 'meta.json')

        # fill in missing artist
        if artist == '':
            artist = lookupArtist(song, album)

        if (artist, album) in trackLists:
            # already seen this album, we can continue
            pass
        else:
            if album == 'self-titled':
                album = artist

            if album == '':
                # Query album name using song
                query = song
            else:
                # Normalise album name
                query = album

            oldAlbum = album
            album = lookupAlbum(query, artist)
            if album != oldAlbum:
                print(f'{song}: "{oldAlbum}" -> "{album}"')
        
        trackNum = lookupTrackNum(artist, album, song)

        json.dump({
            'id': id,
            'name': song,
            'artist': artist,
            'album': album,
            'trackNum': trackNum
        }, f)
        f.close()

    except FileExistsError:
        print(f'meta already exists for {id}')
    
    except LookupError as e:
        print(e)
        print(f'skipping "{song}" by "{artist}"')
    
    return artist, album

def maybeWriteChords(song, rawText):
    id = getID(song)
    try:
        f = openFile(f'./data/{id}', 'chords.txt')
        chords = fixChords(rawText)
        f.write(chords)
        f.close()
    except FileExistsError:
        print(f'chords already exist for {id}')

def getID(song):
    return ''.join(char for char in string.capwords(song) if char.isalnum())

def openFile(dir, filename):
    os.makedirs(dir, exist_ok=True)
    f = open(os.path.join(dir, filename), 'x')
    return f

def fixChords(chords: str):
    chords = chords.strip()
    fixedChords = ''
    lines = chords.split('\n')

    for line in lines:
        if ':' in line:
            spl = line.split(':', 1)
            # Check space before heading
            if not (len(fixedChords) == 0 or fixedChords.endswith('\n\n')):
                fixedChords += '\n'
            fixedChords += spl[0].lower() + ':\n'
            nextLine = spl[1].strip()
            if len(nextLine) > 0:
                fixedChords += nextLine + '\n'
        else:
            line = line.replace('then', '')
            line = line.strip()
            fixedChords += line + '\n'

    return fixedChords

def lookupArtist(song, album):
    if album != '':
        query = album
    else:
        query = song

    res = d.search(query, type='release', format='album')
    # Pick most popular release
    release = res.page(0)[0]
    # for r2 in res.page(0):
    #     if pop(r2) > pop(release):
    #         release = r2

    artist = release.artists[0].name
    print(f'"{song}" is by "{artist}"')
    return artist

# # Popularity of a release
# def pop(release):
#     return vars(release)['data']['community']['have']

def lookupAlbum(query, artist):
    res = d.search(query, artist=artist, type='master', format='album')
    if len(res) == 0:
        res = d.search(query, artist=artist, type='release', format='album')
    if len(res) == 0:
        raise LookupError(f'album not found for query "{query}", artist "{artist}"')

    # Pick the earliest one - heuristic
    release = res.page(0)[0]
    for r2 in res.page(0):
        y2 = int(r2.year)
        if y2 != 0 and y2 < int(release.year):
            release = r2

    album = parseTitle(release.title)[1]
    # print('album:', album)

    # fill in track list
    trackLists[(artist, album)] = [track.title for track in release.tracklist]

    return album

def lookupTrackNum(artist, album, song):
    tracklist = trackLists[(artist, album)]

    try:
        i = tracklist.index(song)
        return i + 1
    except ValueError:
        match = process.extractOne(song, tracklist)
        i = tracklist.index(match[0])
        return i + 1

main()