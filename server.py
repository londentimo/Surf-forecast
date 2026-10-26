"""Python 3.11+; standard library only. Run server or export for static hosting."""
import argparse, concurrent.futures, datetime as dt, html, json, math, os, re, threading, time
import urllib.request, urllib.parse, xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
UTC=dt.timezone.utc
SOURCE='https://micro.windguru.cz/?s=1914&m=gfs&v=WSPD,WDEG,GUST'

def fetch(url):
    with urllib.request.urlopen(url,timeout=30) as response:
        return response.read().decode('utf-8')

def parse_wind(text):
    text=html.unescape(re.sub('<[^>]+>','',text))
    init=re.search(r'GFS 13 km \(init: (\d{4}-\d{2}-\d{2} \d{2}) UTC\)',text)
    if not init or not re.search(r'WSPD\s+WDEG\s+GUST',text) or not re.search(r'knots\s+deg\.\s+knots',text):
        raise ValueError('Unexpected Windguru GFS format or units')
    base=dt.datetime.strptime(init[1],'%Y-%m-%d %H').replace(tzinfo=UTC)
    # Spot forecast uses Europe/Helsinki, including both 03:00s at DST end.
    zone=ZoneInfo('Europe/Helsinki'); year,month=base.year,base.month
    prev_day=base.astimezone(zone).day; previous=None; rows=[]
    for match in re.finditer(r'^\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d+)\.\s+(\d+)h\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*$',text,re.M):
        day,hour=int(match[2]),int(match[3])
        if day<prev_day: month+=1
        if month>12: year+=1;month=1
        prev_day=day
        local=dt.datetime(year,month,day,hour,tzinfo=zone)
        instant=local.astimezone(UTC)
        if previous is not None and instant<=previous:
            instant=local.replace(fold=1).astimezone(UTC)
        if previous is not None and instant<=previous: raise ValueError('Non-monotonic Windguru timestamps')
        if local.strftime('%a')!=match[1]: raise ValueError('Windguru date mismatch')
        previous=instant
        rows.append({'time':instant.isoformat(),'WindSpeedMS':round(float(match[4])*0.514444,3),'WindDirection':float(match[5]),'WindGust':round(float(match[6])*0.514444,3)})
    if len(rows)<8: raise ValueError('Windguru forecast is empty or incomplete')
    if dt.datetime.fromisoformat(rows[-1]['time'])<dt.datetime.now(UTC): raise ValueError('Windguru forecast has expired')
    return rows,base.isoformat()

def waves():
    now=dt.datetime.now(UTC).replace(minute=0,second=0,microsecond=0)
    query=urllib.parse.urlencode({'service':'WFS','version':'2.0.0','request':'getFeature','storedquery_id':'fmi::forecast::wam::point::timevaluepair','latlon':'59.8086,22.9158','parameters':'SigWaveHeight,WavePeriod,WaveDirection','starttime':now.isoformat(),'endtime':(now+dt.timedelta(days=10)).isoformat(),'timestep':'60'})
    root=ET.fromstring(fetch('https://opendata.fmi.fi/wfs?'+query)); result={}
    for obs in root.findall('.//{*}PointTimeSeriesObservation'):
        prop=obs.find('.//{*}observedProperty')
        name=urllib.parse.parse_qs(urllib.parse.urlsplit(prop.get('{http://www.w3.org/1999/xlink}href','')).query).get('param',[''])[0]
        for point in obs.findall('.//{*}MeasurementTVP'):
            value=float(point.find('{*}value').text)
            if math.isfinite(value):
                stamp=dt.datetime.fromisoformat(point.find('{*}time').text.replace('Z','+00:00')).isoformat()
                result.setdefault(stamp,{})[name]=value
    return result

def collect():
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        wind_future=pool.submit(lambda:parse_wind(fetch(SOURCE)))
        wave_future=pool.submit(waves)
        rows,run=wind_future.result() # No silent substitution for Windguru.
        try: wave=wave_future.result();warning=None
        except Exception: wave={};warning='WAM could not be retrieved. Wind outlook remains available.'
    for row in rows: row.update(wave.get(row['time'],{}))
    return {'fetchedAt':dt.datetime.now(UTC).isoformat(),'model':'Windguru · GFS 13 km','modelRun':run,'source':SOURCE,'warning':warning,'rows':rows}

cache=None; cached_at=0; lock=threading.Lock()
def current():
    global cache,cached_at
    with lock:
        if cache is None or time.monotonic()-cached_at>1800:
            cache=collect();cached_at=time.monotonic()
        return cache

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path=='/api/forecast':
            try: body=json.dumps(current(),allow_nan=False).encode();status=200
            except Exception: body=b'{"error":"Windguru could not be refreshed"}';status=502
            mime='application/json'
        elif path in ('/','/index.html','/tulliniemi-forecast.html'):
            body=(ROOT/'index.html').read_bytes();status=200;mime='text/html; charset=utf-8'
        else: body=b'Not found';status=404;mime='text/plain'
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path);args=parser.parse_args()
    if args.export:
        data=collect();args.export.mkdir(parents=True,exist_ok=True)
        page=(ROOT/'index.html').read_text()
        page=re.sub(r'<script id="forecast-snapshot" type="application/json">.*?</script>',lambda _: '<script id="forecast-snapshot" type="application/json">'+json.dumps(data,allow_nan=False).replace('<','\\u003c')+'</script>',page,flags=re.S)
        (args.export/'index.html').write_text(page)
        (args.export/'forecast.json').write_text(json.dumps(data,allow_nan=False))
        print(f'Exported {len(data["rows"])} Windguru rows to {args.export}')
    else:
        port=int(os.getenv('PORT','8000'));print(f'Open http://localhost:{port}',flush=True)
        ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
