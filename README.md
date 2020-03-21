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

- We will collapse all the artist_name by selecting the common strings in artist_name columns for each artist_id