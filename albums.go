package main

import (
	"fmt"

	"github.com/barrettj12/chords/src/client"
)

func main() {
	c, err := client.NewClient("http://localhost:8080", "")
	if err != nil {
		panic(err)
	}

	albums := map[string][]string{}
	artists, err := c.GetArtists()
	if err != nil {
		panic(err)
	}

	for _, artist := range artists {
		albumList := set{}
		songs, err := c.GetSongs(&artist, nil, nil)
		if err != nil {
			panic(err)
		}
		for _, song := range songs {
			albumList.add(song.Album)
		}
		albums[artist] = albumList
	}

	// Print albums
	for artist, albumList := range albums {
		fmt.Println(artist)
		for _, album := range albumList {
			fmt.Println("-", album)
		}
	}
}

type set []string

func (s *set) add(v string) {
	if !s.contains(v) {
		*s = append(*s, v)
	}
}

func (s *set) contains(v string) bool {
	for _, w := range *s {
		if w == v {
			return true
		}
	}
	return false
}
