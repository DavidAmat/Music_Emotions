
/*
#####################################################
#####################################################
# Create database to help the creation of YT queries
#####################################################
#####################################################
*/

create table youtube_url as
select track_id, title, artist_id, artist_name, '' as yt_url, duration, year
from songs;

CREATE UNIQUE INDEX idx_tid ON youtube_url (
    track_id
);


/*
#####################################################
#####################################################
# Create database for OUTPUT of
#####################################################
#####################################################
*/
create table match (track_id INTEGER, url TEXT, batch_id INTEGER);
create table nonmatch (track_id INTEGER, query TEXT, batch_id INTEGER);

select * from match
select * from nonmatch

/*
delete from match where 1=1
delete from nonmatch where 1=1
*/


select * from youtube_url limit 100;
select * from youtube_url where artist_id = 'AR00MBZ1187B9B5DB1'
select * from (select artist_id, count(distinct(artist_name)) as ct from youtube_url group by artist_id) where ct > 1;