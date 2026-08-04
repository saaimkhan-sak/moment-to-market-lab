"""Official public-channel metadata; no private analytics or historical performance inference."""
from __future__ import annotations
import csv, json, os, sys, time
from urllib.parse import urlencode
from common import ROOT, archive_json, evidence_record, fetch_json, load_env, now_utc, write_json

BASE = "https://www.googleapis.com/youtube/v3/"

def request(resource: str, **params):
    url = BASE + resource + "?" + urlencode(params)
    payload, provenance = fetch_json(url)
    # API keys belong only in .env. Provenance records the reproducible request
    # parameters without persisting the credential in raw archives or outputs.
    provenance["source_url"] = BASE + resource + "?" + urlencode({k:v for k,v in params.items() if k != "key"})
    return payload, provenance

def ingest_complete_club(club_id: str, channel_id: str) -> dict:
    """Archive and materialize every accessible upload from a verified channel."""
    load_env(); key=os.getenv("YOUTUBE_API_KEY")
    if not key:
        return {"club_id":club_id,"channel_id":channel_id,"evidence_status":"unavailable","reason":"YOUTUBE_API_KEY is not set"}
    channel, channel_provenance=request("channels",part="id,contentDetails,snippet,statistics",id=channel_id,key=key)
    items=channel.get("items",[])
    if len(items)!=1 or items[0].get("id")!=channel_id:
        return {"club_id":club_id,"channel_id":channel_id,"evidence_status":"unavailable","reason":"verified channel ID did not resolve uniquely"}
    archive_json("youtube",f"complete-{club_id.lower()}-channel",channel,channel_provenance)
    uploads=items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids=[]; playlist_pages=0; page_token=None
    while True:
        params={"part":"contentDetails","playlistId":uploads,"maxResults":50,"key":key}
        if page_token: params["pageToken"]=page_token
        payload, provenance=request("playlistItems",**params); playlist_pages+=1
        archive_json("youtube",f"complete-{club_id.lower()}-uploads-{playlist_pages:04d}",payload,provenance)
        video_ids.extend(item["contentDetails"]["videoId"] for item in payload.get("items",[]) if item.get("contentDetails",{}).get("videoId"))
        page_token=payload.get("nextPageToken")
        if not page_token: break
        time.sleep(.05)
    # Preserve playlist order while removing any accidental duplicate IDs.
    video_ids=list(dict.fromkeys(video_ids)); records=[]; video_pages=0
    for offset in range(0,len(video_ids),50):
        batch=video_ids[offset:offset+50]
        payload, provenance=request("videos",part="snippet,contentDetails,statistics",id=",".join(batch),maxResults=50,key=key); video_pages+=1
        archive_json("youtube",f"complete-{club_id.lower()}-videos-{video_pages:04d}",payload,provenance)
        for video in payload.get("items",[]):
            snippet=video.get("snippet",{}); details=video.get("contentDetails",{}); stats=video.get("statistics",{})
            records.append({"club_id":club_id,"video_id":video["id"],"channel_id":snippet.get("channelId"),"published_at":snippet.get("publishedAt"),"title":snippet.get("title"),"description":snippet.get("description"),"duration":details.get("duration"),"view_count":stats.get("viewCount"),"like_count":stats.get("likeCount"),"comment_count":stats.get("commentCount"),"retrieved_at":provenance["retrieved_at"],"source_url":f"https://www.youtube.com/watch?v={video['id']}","evidence_status":"confirmed"})
        time.sleep(.05)
    returned={row["video_id"] for row in records}; inaccessible=[video_id for video_id in video_ids if video_id not in returned]
    write_json(f"data/curated/youtube_complete_{club_id.lower()}.json",records)
    result={"club_id":club_id,"channel_id":channel_id,"channel_title":items[0].get("snippet",{}).get("title"),"uploads_playlist_id":uploads,"playlist_video_ids":len(video_ids),"accessible_videos":len(records),"inaccessible_or_deleted_videos":len(inaccessible),"inaccessible_video_ids":inaccessible,"playlist_pages":playlist_pages,"video_detail_pages":video_pages,"oldest_accessible_published_at":min((r["published_at"] for r in records if r.get("published_at")),default=None),"newest_accessible_published_at":max((r["published_at"] for r in records if r.get("published_at")),default=None),"retrieved_at":channel_provenance["retrieved_at"],"source_url":channel_provenance["source_url"],"evidence_status":"confirmed" if len(records)+len(inaccessible)==len(video_ids) else "unavailable"}
    write_json(f"data/manifests/youtube_complete/{club_id}.json",result)
    return result

def ingest_complete_registry() -> str:
    registry=list(csv.DictReader((ROOT/"config/official_channel_registry.csv").open())); results=[]; all_records=[]
    for index,row in enumerate(registry,1):
        if row["evidence_status"]!="confirmed" or not row["official_channel_id"]:
            result={"club_id":row["club_id"],"evidence_status":"unavailable","reason":"channel_not_verified"}
        else:
            try: result=ingest_complete_club(row["club_id"],row["official_channel_id"])
            except Exception as exc: result={"club_id":row["club_id"],"evidence_status":"unavailable","reason":type(exc).__name__}
        results.append(result)
        club_path=ROOT/f"data/curated/youtube_complete_{row['club_id'].lower()}.json"
        if result.get("evidence_status")=="confirmed" and club_path.exists(): all_records.extend(json.loads(club_path.read_text()))
        write_json("data/manifests/youtube_complete_acquisition.json",{"source":evidence_record("youtube","confirmed","Complete accessible upload histories from verified official channel upload playlists."),"completed_clubs":sum(x.get("evidence_status")=="confirmed" for x in results),"total_clubs":len(registry),"results":results})
        print(f"[{index}/{len(registry)}] {row['club_id']}: {result.get('evidence_status')} {result.get('accessible_videos','-')} accessible videos",flush=True)
        time.sleep(.15)
    if len(results)==32 and all(x.get("evidence_status")=="confirmed" for x in results): write_json("data/curated/content_video.json",all_records)
    return str(ROOT/"data/manifests/youtube_complete_acquisition.json")

def ingest(channel_handle: str, limit: int = 50) -> str:
    load_env()
    key = os.getenv("YOUTUBE_API_KEY")
    safe_name = channel_handle.lstrip('@').lower()
    if not key:
        return str(write_json(f"data/evidence/youtube-{safe_name}.json", {"channel_handle": channel_handle, "source_url": "https://developers.google.com/youtube/v3/docs", "retrieved_at": now_utc(), "evidence_status": "unavailable", "reason": "YOUTUBE_API_KEY is not set"}))
    channel, provenance = request("channels", part="id,contentDetails,snippet,statistics", forHandle=channel_handle.lstrip('@'), key=key)
    archive_json("youtube", f"{safe_name}-channel", channel, provenance)
    items = channel.get("items", [])
    if len(items) != 1:
        return str(write_json(f"data/evidence/youtube-{safe_name}.json", {"channel_handle":channel_handle,"source_url":provenance["source_url"],"retrieved_at":provenance["retrieved_at"],"evidence_status":"unavailable","reason":"Official channel handle did not resolve uniquely"}))
    channel_item = items[0]; uploads = channel_item["contentDetails"]["relatedPlaylists"]["uploads"]
    playlist, playlist_provenance = request("playlistItems", part="contentDetails", playlistId=uploads, maxResults=limit, key=key)
    archive_json("youtube", f"{safe_name}-uploads", playlist, playlist_provenance)
    ids = [item["contentDetails"]["videoId"] for item in playlist.get("items", []) if item.get("contentDetails", {}).get("videoId")]
    videos, video_provenance = request("videos", part="snippet,contentDetails,statistics", id=",".join(ids), maxResults=limit, key=key) if ids else ({"items": []}, provenance)
    archive_json("youtube", f"{safe_name}-videos", videos, video_provenance)
    records=[]
    for video in videos.get("items", []):
        s=video.get("snippet",{}); c=video.get("contentDetails",{}); stats=video.get("statistics",{})
        records.append({"video_id":video["id"],"channel_id":s.get("channelId"),"published_at":s.get("publishedAt"),"title":s.get("title"),"description":s.get("description"),"duration":c.get("duration"),"view_count":stats.get("viewCount"),"like_count":stats.get("likeCount"),"comment_count":stats.get("commentCount"),"retrieved_at":video_provenance["retrieved_at"],"source_url":f"https://www.youtube.com/watch?v={video['id']}","evidence_status":"confirmed"})
    write_json(f"data/curated/youtube-{safe_name}.json", records)
    return str(write_json(f"data/evidence/youtube-{safe_name}.json", {"channel_handle":channel_handle,"channel_id":channel_item["id"],"uploads_playlist_id":uploads,"source_url":"https://developers.google.com/youtube/v3/docs","retrieved_at":video_provenance["retrieved_at"],"evidence_status":"confirmed","sample_size":len(records),"limitation":"Current public counts are descriptive snapshots, not historical 24-hour or 72-hour video performance."}))

def plan_club_channels() -> str:
    known={r["club_id"]:r for r in csv.DictReader((ROOT/"config/official_channel_registry.csv").open())}
    rows=[]
    for club in csv.DictReader((ROOT/"config/clubs.csv").open()):
        record=known.get(club["club_id"])
        rows.append({"club_id":club["club_id"],"club_name":club["club_name"],"official_handle":record["official_youtube_handle"] if record else None,"evidence_status":record["evidence_status"] if record else "unknown","next_step":"Use a dated official club/NHL page to verify the channel before API acquisition; never infer a handle from naming convention."})
    return str(write_json("data/manifests/youtube_club_channel_plan.json", {"source":evidence_record("youtube","planned"),"rows":rows}))

def discover_candidates() -> str:
    """Find exact-title channel candidates; discovery is not official verification."""
    load_env(); key=os.getenv('YOUTUBE_API_KEY')
    if not key: return str(write_json('data/manifests/youtube_channel_candidates.json', {'source':evidence_record('youtube','unavailable','YOUTUBE_API_KEY is not set'),'rows':[]}))
    rows=[]
    for club in csv.DictReader((ROOT/'config/clubs.csv').open()):
        payload, provenance=request('search', part='snippet', q=club['club_name'], type='channel', maxResults=5, key=key)
        archive_json('youtube', f"{club['club_id'].lower()}-channel-search", payload, provenance)
        candidates=[]
        for item in payload.get('items',[]):
            snippet=item.get('snippet',{}); cid=(item.get('id') or {}).get('channelId')
            candidates.append({'channel_id':cid,'title':snippet.get('channelTitle'),'description':snippet.get('description'),'published_at':snippet.get('publishedAt')})
        exact=[x for x in candidates if (x.get('title') or '').casefold()==club['club_name'].casefold()]
        rows.append({'club_id':club['club_id'],'club_name':club['club_name'],'evidence_status':'candidate_pending_official_verification','candidate':exact[0] if len(exact)==1 else None,'candidate_count':len(candidates),'source_url':provenance['source_url'],'retrieved_at':provenance['retrieved_at'],'all_candidates':candidates})
        time.sleep(.15)
    return str(write_json('data/manifests/youtube_channel_candidates.json', {'source':evidence_record('youtube','confirmed','API candidate discovery only; official verification remains separate.'),'rows':rows}))

def materialize_verified_registry() -> str:
    load_env(); key=os.getenv('YOUTUBE_API_KEY')
    verified=list(csv.DictReader((ROOT/'config/youtube_verified_channel_ids.csv').open()))
    if not key: return str(write_json('data/manifests/youtube_verified_registry.json', {'source':evidence_record('youtube','unavailable','YOUTUBE_API_KEY is not set'),'rows':[]}))
    rows=[]
    for offset in range(0,len(verified),50):
        batch=verified[offset:offset+50]
        payload, provenance=request('channels',part='id,snippet,contentDetails,statistics',id=','.join(x['channel_id'] for x in batch),maxResults=50,key=key)
        archive_json('youtube',f'verified-channels-{offset//50+1}',payload,provenance)
        by_id={x['id']:x for x in payload.get('items',[])}
        for source in batch:
            item=by_id.get(source['channel_id']); snippet=(item or {}).get('snippet',{})
            rows.append({**source,'official_youtube_handle':snippet.get('customUrl',''),'channel_title':snippet.get('title',''),'api_evidence_status':'confirmed' if item else 'unavailable','api_source_url':provenance['source_url'],'api_retrieved_at':provenance['retrieved_at']})
    path=ROOT/'config/official_channel_registry.csv'
    fields=['club_id','official_youtube_handle','official_channel_id','evidence_status','source_url','retrieved_at','notes']
    with path.open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({'club_id':row['club_id'],'official_youtube_handle':row['official_youtube_handle'],'official_channel_id':row['channel_id'],'evidence_status':'confirmed' if row['api_evidence_status']=='confirmed' else 'unavailable','source_url':row['verification_source_url'],'retrieved_at':row['retrieved_at'],'notes':row['verification_basis']})
    return str(write_json('data/manifests/youtube_verified_registry.json', {'source':evidence_record('youtube','confirmed','Channel-page verification evidence plus API ID resolution.'),'rows':rows}))

def ingest_registry() -> str:
    results=[]
    for row in csv.DictReader((ROOT/'config/official_channel_registry.csv').open()):
        if row['evidence_status']!='confirmed' or not row['official_youtube_handle']:
            results.append({'club_id':row['club_id'],'evidence_status':'unavailable','reason':'channel_not_verified'}); continue
        try:
            results.append({'club_id':row['club_id'],'evidence_status':'confirmed','path':ingest(row['official_youtube_handle'])})
        except Exception as exc:
            results.append({'club_id':row['club_id'],'evidence_status':'unavailable','reason':type(exc).__name__})
        time.sleep(.15)
    return str(write_json('data/manifests/youtube_full_league_acquisition.json', {'source':evidence_record('youtube','confirmed','Verified public club channels; current public statistics only.'),'rows':results}))

if __name__ == "__main__":
    if sys.argv[1:] == ['--plan-clubs']: print(plan_club_channels())
    elif sys.argv[1:] == ['--discover-candidates']: print(discover_candidates())
    elif sys.argv[1:] == ['--materialize-verified-registry']: print(materialize_verified_registry())
    elif sys.argv[1:] == ['--ingest-registry']: print(ingest_registry())
    elif sys.argv[1:] == ['--ingest-complete-registry']: print(ingest_complete_registry())
    else: print(ingest(sys.argv[1]))
