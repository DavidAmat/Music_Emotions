create table youtube_url as
select track_id, title, artist_id, artist_name, '' as yt_url, duration, year
from songs;

CREATE UNIQUE INDEX idx_tid ON youtube_url (
    track_id
);


select * from youtube_url limit 100;
select * from youtube_url where artist_id = 'AR00MBZ1187B9B5DB1'
select * from (select artist_id, count(distinct(artist_name)) as ct from youtube_url group by artist_id) where ct > 1;