# Music_Emotions

## Setting up the environment

- Create a pipenv environment
- Use `pipenv shell` to activate environment
- Use `pipenv install <package>` to install packages
- Use `pipenv install jupyter` and `pipenv run jupyter notebook` to launch notebook

- For more commands look at  `/notes/pipenv_manual.md`

- Hola Marta


- Hola Marta desde la branca David
- Hello David

- Prova final 

## WebScrapping

- We find that for each artist_id there can be multiple artist names:
```sql
select * from (select artist_id, count(distinct(artist_name)) as ct from youtube_url group by artist_id) where ct > 1;
#returns 13,781 rows
/*
artist_id			artist_name
AR006821187FB5192B	Stephen Varcoe/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe
AR006821187FB5192B	Stephen Varcoe/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe
AR006821187FB5192B	Stephen Varcoe/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe/John Wells/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe; Cappella Coloniensis; William Christie
*/
```

- We do longest common substring intersection. We will save all the artist_id and the common substring intersection in a dictionary to see for all the 44,700 artists, how many can we find a unique name that matches all the registers (artist_name) with that artist_id. To do so we create 2 dictionaries to store the artist_id if we can find a common substring in the artist_names and one dictionary for the deleted artists. **Here we lose 700 artist_id in which they did not have a common artist_name**. We are left with 43,000 artists. For each artist in the common longest substring, we have to ensure that the common string is not just 2 letters (i.e artists = ["ABBA", "BANANAS"] then the common substring will be "BA", but "BA" is not in the set of artists!)

- We will load a df for each artist and create the query to Youtube via Selenium

- Once we have the results, we scan each title from youtube and impose that **all words in the title in MSD are present in the youtube title doing set intersections**. 