# Music_Emotions



## Setting up the environment

- Create a pipenv environment
- Use `pipenv shell` to activate environment
- Use `pipenv install <package>` to install packages
- Use `pipenv install jupyter` and `pipenv run jupyter notebook` to launch notebook

- For more commands look at  `/notes/pipenv_manual.md`


## WebScrapping Codes

### Code 1. Data Cleaning

- Start from the database raw.db. This database is created to store all initial tables in the MSD. We will use the database clean.db to upload the results for the data cleaning part.

#### 1.2 Get the set of artists

- Retrieve all the artists ID and names.

#### 1.3 Get the songs for one artist

- We find that for each artist_id there can be multiple artist names:

```sql
select * from (select artist_id, count(distinct(artist_name)) as ct from youtube_url group by artist_id) where ct > 1;
#returns 13,781 rows
/*
AR006821187FB5192B	Stephen Varcoe/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe
AR006821187FB5192B	Stephen Varcoe/John Wells/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe; Cappella Coloniensis; William Christie
*/
```

- We do longest common substring intersection. We will save all the artist_id and the common substring intersection in a dictionary to see for all the 44,700 artists, how many can we find a unique name that matches all the registers (artist_name) with that artist_id. 

- To do so we create 2 dictionaries to store the artist_id if we can find a common substring in the artist_names and one dictionary for the deleted artists. **Here we lose 700 artist_id in which they did not have a common artist_name**. We are left with 43,000 artists. For each artist in the common longest substring, we have to ensure that the common string is not just 2 letters (i.e artists = ["ABBA", "BANANAS"] then the common substring will be "BA", but "BA" is not in the set of artists!).

- We scan all the songs for one artist ID. If it has only 1 song, we keep that artist name as it is. If it has multiple artist names, we scan all the names and find the commong longest substring. If no commong substring then this artist is discarded (**dict_artistId2NOTquery**). If it finds a common substring for the artist name we will put it in the dictionary **dict_artistId2artistQuery**. The values for that dictionary will not be yet the query, since we have to ensure that the longest common substring makes sense as a artist name by comparing to any artist name in the database.

- To do this check, we create a **set of pairs artist_id-artist_name** for all the pairs in the YOUTUBE_URL table. We then scan **dict_artistId2artistQuery** and see if that pair ARTIST_ID (key of the dictionary) - COMMON_LONGEST_SUBSTRING (value of the dictionary) has a corresponding pair in the **set of pairs artist_id-artist_name** for the MSD dataset. For example:

```sql
/*
AR006821187FB5192B	Stephen Varcoe/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe
AR006821187FB5192B	Stephen Varcoe/John Wells/Choir of King's College_ Cambridge/Sir David Willcocks
AR006821187FB5192B	Stephen Varcoe; Cappella Coloniensis; William Christie
*/
```

- The longest common substring is `Stephen Varcoe`. So in the dictionary above there will be a key-value pair like this:
```sql
/*
AR006821187FB5192B	Stephen Varcoe
*/
```

- Then we will look at the **set of pairs artist_id-artist_name** for the MSD dataset and realize that there is a register that is just the same as that (the second register was that case). Hence, for that artist_id we will keep that name to account for all the songs of that ID. **This name "Stephen Varcoe" is named the "consensus artist name"** as it is a consensus over all possibilities for that ARTIST ID with different names. 

- We then apply another filter to remove consensus names with only a number and with only 1 letter. 


#### 2. Create an internal identifier

- Here we create the **artist_iid** standing for "artist internal identifier". This will be a sequential identifier that we put in order to ease the ordering and identification of the artists for ourselves. This is done by removing all duplicated artist names in the consensus dataframe and just get **unique artist names**. We want this unicity because when querying in Youtube, we only want to query each artist ONCE. 

#### 3. Join that internal identifier to the full database of MSD

- We do a SELECT * from youtube_url to get all the songs and finally **do an INNER join with the consensus dataframe**. This join is performed on **artist_id** 

#### 3.1 Create the clean.db

- Once we have such data cleaned and with a unique identifier per artist name we create the clean.db (the code of the creation of the database is in the **queries.sql** file in the webscrapping folder).

- We create a table called **youtube_url** to save that table (the one comming from the inner join).

### Code 2. WebScrapping

- Here we have 2 versions, one is the jupyter notebook version, that was the development and the other is the .py version which is completed with the **argv** option to select batches of artist.

- The idea is to create batches of 1,000 artists to query in Youtube to avoid banning.

#### 1. Load the clean database

- Do a select * from youtube_url to get all the fields

#### 1.1 Create useful fields

- We create a field that is going to be **tit_art** which will be the combination of both the title and the artist name. This is done when searching for song titles in youtube, we want both the artist and the song name to appear in the youtube title.

- All queries and comparisons will be performed on **lowercase** strings.

#### 2. WebScrapping functions

We have 3 functions:
- **fun_clean_title**: gets a "tit_art" from MSD and cleans it to remove parenthesis (i.e (Explicit Version)). Only allowing by a regular expression strings starting by letters a-z.
- **get_MSD_title_Match_yt_title**: this is the most complex function. Basically it loops through all the youtube songs that has encountered the webscrapping. For each youtube (yt) song, if splits its words in a **set**. So, for **one yt song** it scans through **all the songs of that artist in the MSD**. For each comparison, it makes the intersection of the **set of yt title words** with the **MSD title words** (cleaned with the **fun_clean**). We will consider a **match** (meaning that we have found a soung from the youtube results of the query that matches a song for that artist in the MSD) only if the *length* of the set intersected is the same as the length of the set of the MSD title. For example:

```sql
/*
Artist Name: Coldplay

Youtube title: Fix You -> set: {"fix", "you"} -> (length = 2) !!!!!!

MSD songs for Coldplay
- Viva la vida: {"viva", "la", "vida"} -> intsersection with Youtube title is EMPTY
- Clocks: {"clocks"} -> intsersection with Youtube title is EMPTY
- Fix You (Official Video): {"fix", "you", "(Official", "Video)"} -> intsersection with Youtube title is {"fix", "you"} -> length = 2 !!!!!!
*/
```

That said, we see how the length match in this case = 2. So we will add this title and the href (youtube URL) to the **list_matching** list, which is one argument returned by this function. What the algorithm next does is it removes "Fix You" from the list of MSD songs for Coldplay, so now, we list will look:

```sql
/*
Artist Name: Coldplay

Youtube title: Paradise

MSD songs for Coldplay
- Viva la vida: {"viva", "la", "vida"} -> intsersection with Youtube title is EMPTY
- Clocks: {"clocks"} -> intsersection with Youtube title is EMPTY
*/
```

So when inspecting the next title in youtube (i.e Paradise) the list of songs that it has to examine if it matches a MSD song has diminished. Since the Fix you song have already been found. This optimizes the search time and prevents that if there are multiple videos of the same song, the algorithm WILL NOT get all the URLs of that song name if it has already found 1.

- **WebScrapperYoutube**: this function takes the dataframe of the current batch and performs the webscrapping, so for each artist it applies the **get_MSD_title_Match_yt_title** function. Since it loops throuh all the rows (this loop has to be seen as a loop over artist names) we create 2 dictionaries:
- **dict_matching**: dictionary with primary key as artist_name, and with values a list of tuples, where each tuple is (track_id, youtube URL).
- **dict_non_matching**: for the songs that have not been found in youtube, it creates a primary key with the artist_name, and a list of tuples where each tuple is (titart, trackid). The idea is that with that dictionary we will create another database to look especifically in youtube the query: TITLE + ARTIST since we have seen that only looking at that ARTIST in youtube does not lead to any result. 

#### 3. WebScrapping calling functions on the batch artists

- Now we create a dataframe at the **artist_iid** level. This is done because we want to do queries at youtube at the artist level, so a dataframe at the song level will not help. What we will do is create a dataframe grouping by artist_iid (the artist name will be unique for that artist_iid) and then create a column name **tuple_titart_trackid** in that dataframe( **df_list_tit_art**). This column will be a list of tuples, consisting of (titart, trackid). Remind that titart = title + " " + artist concatenation of strings. 

- Now we SORT that **df_list_tit_art** by artist_iid and **apply the batch num** to get a subset of artists (1,000) for that batch.

- This subsample will be called **df_WebScrapping**.

- We call the function **WebScrapperYoutube** and get the two dictionaries as output (**dmatch** and **dnonmatch**)

- For the **dmatch** we insert the **dmatch** tuples for each artist **adding the batch_num** to identify which inserts come from each batch in the table **match**.

- For the **dnonmatch**, we inser that dictionary to the table **nonmatch** with also the batch_num. The idea is to **replicate the webscrapping code for this specific queries (tit + art) to try if we can find that song when querying especifically for that song in youtube**. FOr the cases in which we will not be able to look for the video will be totally lost but for cases in which querying for the title + artist name helps, we will recover them. This will be done in another code, not this one. 


### Code 3. Re-querying non matched artists

