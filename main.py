from nicegui import ui
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# --- SETUP DATABASE ---
load_dotenv() 
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

ui.page_title('Asset Register')

# --- MUJI THEME ENGINE ---
# 1. Override the default vibrant colors with muted Muji tones
ui.colors(
    primary='#7F0019',    # Muji signature deep red
    secondary='#F5F5F5',  # Muted light grey
    accent='#737373',     # Dark grey for secondary text
    positive='#4A6741',   # Muted earthy green
)

# 2. Force the entire app background to a warm, unbleached paper color
ui.query('body').classes('bg-[#FAF9F6] text-[#333333]')

# --- DATA FUNCTIONS ---
def get_assets():
    response = supabase.table("assets").select("asset_tag, name, purchase_price, status, categories(name), locations(name)").execute()
    assets = []
    for row in response.data:
        assets.append({
            'asset_tag': row['asset_tag'],
            'name': row['name'],
            'category': row['categories']['name'] if row['categories'] else 'N/A',
            'location': row['locations']['name'] if row['locations'] else 'N/A',
            'status': row['status'],
            'price': f"RM {row['purchase_price']:,.2f}"
        })
    return assets

# --- UI LAYOUT ---

# Header: Crisp white background, thin border, zero shadow
with ui.header().classes('bg-[#8b6854] border-b border-stone-200 text-[#333333] items-center justify-between px-8 py-3 shadow-none'):
    # A simple, elegant title
    ui.label('Plantation Fixed Assets').classes('text-xl tracking-wide font-light')
    
    # "Flat" button style for logout to keep it minimal
    ui.button('Sign Out', color='accent').props('flat').classes('text-sm tracking-wider')

# Main Container: Center the content and restrict the width so it doesn't stretch too far on wide monitors
with ui.column().classes('w-full max-w-5xl mx-auto mt-8 px-4'):

    # Tabs: Clean, underlined style rather than heavy colored blocks
    with ui.tabs().classes('w-full border-b border-stone-200 text-stone-500') as tabs:
        tab_add = ui.tab('Register Equipment')
        tab_view = ui.tab('Asset Register')

    with ui.tab_panels(tabs, value=tab_view).classes('w-full bg-transparent p-0 mt-6'):
        
        # --- TAB 1: VIEW REGISTER ---
        with ui.tab_panel(tab_view):
            
            # The Table: .props('flat bordered') removes the shadow and adds a crisp line
            columns = [
                {'name': 'asset_tag', 'label': 'Tag', 'field': 'asset_tag', 'align': 'left'},
                {'name': 'name', 'label': 'Description', 'field': 'name', 'align': 'left'},
                {'name': 'category', 'label': 'Category', 'field': 'category', 'align': 'left'},
                {'name': 'location', 'label': 'Location', 'field': 'location', 'align': 'left'},
                {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
                {'name': 'price', 'label': 'Price', 'field': 'price', 'align': 'right'},
            ]
            
            asset_data = get_assets()
            ui.table(columns=columns, rows=asset_data, row_key='asset_tag').classes('w-full text-stone-800').props('flat bordered')

        # --- TAB 2: ADD ASSET ---
        with ui.tab_panel(tab_add):
            
            # Form Card: Pure white, thin border, sharp corners (rounded-sm)
            with ui.card().classes('w-full max-w-2xl bg-white border border-stone-200 shadow-none rounded-sm p-8 mx-auto'):
                ui.label('New Asset Details').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-6 w-full')
                
                # Inputs: outlined props make them look like simple paper forms
                asset_tag = ui.input('Asset Tag (e.g., TRAC-2026-001)').classes('w-full mb-2').props('outlined dense')
                name = ui.input('Description').classes('w-full mb-2').props('outlined dense')
                status = ui.select(['Active', 'In Maintenance', 'Disposed'], value='Active', label='Status').classes('w-full mb-6').props('outlined dense')
                
                def save_asset():
                    ui.notify(f'Recorded {asset_tag.value}', position='top', type='positive')
                    asset_tag.value = ''
                    name.value = ''
                    
                # Primary Button: Uses that signature Muji Red, unelevated
                ui.button('Save Record', on_click=save_asset).classes('w-full py-2 tracking-wide font-light').props('unelevated')

# --- RUN THE APP ---
port = int(os.environ.get("PORT", 8080))
ui.run(title="Asset App", host="0.0.0.0", port=port)