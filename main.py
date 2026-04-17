from nicegui import ui
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# --- SETUP DATABASE ---
load_dotenv() # This loads the passwords from your .env file
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

ui.page_title('🏢 Fixed Asset Management')

# --- DATA FUNCTIONS ---
def get_assets():
    # Fetch data and flatten the categories/locations just like we did yesterday
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
# Create a nice top navigation bar
with ui.header().classes('bg-amber-8 text-white items-center justify-between'):
    ui.label('Plantation Fixed Asset Register').classes('text-h6 font-bold')

# Create Tabs
with ui.tabs().classes('w-full') as tabs:
    tab_add = ui.tab('➕ Add New Asset')
    tab_view = ui.tab('📋 Asset Register')

with ui.tab_panels(tabs, value=tab_view).classes('w-full'):
    
    # --- TAB 1: ADD ASSET ---
    with ui.tab_panel(tab_add):
        ui.label('Register Equipment').classes('text-xl font-bold mb-4')
        
        # NiceGUI uses 'cards' to make clean, white container boxes
        with ui.card().classes('w-full max-w-2xl'):
            asset_tag = ui.input('Asset Tag (e.g., TRAC-2026-001)').classes('w-full')
            name = ui.input('Description').classes('w-full')
            status = ui.select(['Active', 'In Maintenance', 'Disposed'], value='Active', label='Status').classes('w-full')
            
            def save_asset():
                # Logic to save to Supabase would go here
                ui.notify(f'Successfully saved {asset_tag.value}!', type='positive')
                asset_tag.value = ''
                name.value = ''
                
            ui.button('Save Asset', on_click=save_asset).classes('mt-4 bg-green-6 text-white')

    # --- TAB 2: VIEW REGISTER ---
    with ui.tab_panel(tab_view):
        ui.label('Current Asset Register').classes('text-xl font-bold mb-4')
        
        # Define the columns for the data table
        columns = [
            {'name': 'asset_tag', 'label': 'Tag', 'field': 'asset_tag', 'align': 'left'},
            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
            {'name': 'category', 'label': 'Category', 'field': 'category', 'align': 'left'},
            {'name': 'location', 'label': 'Location', 'field': 'location', 'align': 'left'},
            {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center'},
            {'name': 'price', 'label': 'Price', 'field': 'price', 'align': 'right'},
        ]
        
        # Load the data and build the table
        asset_data = get_assets()
        ui.table(columns=columns, rows=asset_data, row_key='asset_tag').classes('w-full')

# --- RUN THE APP ---
ui.run(title="Asset App", port=8080) # "testing change"