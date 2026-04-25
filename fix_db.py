import os, dotenv
dotenv.load_dotenv()
from supabase import create_client

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_ANON_KEY')
db = create_client(url, key)

try:
    sql = 'CREATE POLICY "Authenticated users can update" ON public.market_intelligence FOR UPDATE TO authenticated USING (true) WITH CHECK (true);'
    res = db.rpc('exec_sql', {'query': sql}).execute()
    print('SUCCESS')
except Exception as e:
    print('ERROR:', e)
