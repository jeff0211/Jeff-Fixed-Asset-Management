from nicegui import ui
from supabase import create_client, Client
import os
import csv
import io
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
    response = supabase.table("assets").select("asset_tag, name, purchase_price, status, categories(name), locations(name)").order("id", desc=True).execute()
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
with ui.header().classes('bg-[#8b6854] border-b border-stone-200 text-white items-center justify-between px-8 py-3 shadow-none'):
    # A simple, elegant title
    ui.label('Fixed Assets Module Demo').classes('text-xl tracking-wide font-light')
    
    # "Flat" button style for logout to keep it minimal
    ui.button('Sign Out', color='accent').props('flat').classes('text-sm tracking-wider')

# Main Container: Center the content and restrict the width so it doesn't stretch too far on wide monitors
with ui.column().classes('w-full max-w-5xl mx-auto mt-8 px-4'):

    # Tabs: Clean, underlined style rather than heavy colored blocks, aligned to stretch equally
    with ui.tabs().classes('w-full border-b border-stone-200 text-stone-500').props('align="justify"') as tabs:
        tab_dashboard = ui.tab('Dashboard', icon='dashboard')
        tab_add = ui.tab('Addition', icon='add_box')
        tab_disposal = ui.tab('Disposal', icon='delete')
        tab_reports = ui.tab('Reports', icon='bar_chart')
        tab_maintenance = ui.tab('Maintenance', icon='build')

    # Default to Dashboard tab
    with ui.tab_panels(tabs, value=tab_dashboard).classes('w-full bg-transparent p-0 mt-6'):
        
        # --- TAB: DASHBOARD ---
        with ui.tab_panel(tab_dashboard):
            with ui.card().classes('w-full bg-white border border-stone-200 shadow-none rounded-sm p-12 flex flex-col items-center justify-center'):
                ui.icon('dashboard', size='4rem').classes('text-stone-200 mb-4')
                ui.label('Dashboard Overview').classes('text-2xl text-stone-400 font-light mb-2')
                ui.label('Key Performance Indicators and charts will be displayed here.').classes('text-stone-400')

        # --- TAB: ADD ASSET ---
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
                
        # --- TAB: DISPOSAL ---
        with ui.tab_panel(tab_disposal):
            with ui.card().classes('w-full bg-white border border-stone-200 shadow-none rounded-sm p-12 flex flex-col items-center justify-center'):
                ui.icon('delete', size='4rem').classes('text-stone-200 mb-4')
                ui.label('Asset Disposal').classes('text-2xl text-stone-400 font-light mb-2')
                ui.label('Process write-offs and asset retirement here.').classes('text-stone-400')

        # --- TAB: REPORTS (Including Asset Register) ---
        with ui.tab_panel(tab_reports):
            
            # Header Row with Title and Export Button
            with ui.row().classes('w-full items-center justify-between mb-4 px-2'):
                ui.label('Comprehensive Asset Register').classes('text-xl text-stone-800 font-light')
                
                def export_csv():
                    data = get_assets()
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(['Asset Tag', 'Description', 'Category', 'Location', 'Status', 'Price'])
                    for row in data:
                        writer.writerow([row['asset_tag'], row['name'], row['category'], row['location'], row['status'], row['price']])
                    ui.download(output.getvalue().encode('utf-8'), 'asset_register.csv')
                    ui.notify('Download started', type='positive')
                
                ui.button('Export to CSV', icon='download', on_click=export_csv).classes('text-sm tracking-wide bg-[#7F0019] text-white').props('unelevated')

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
            ui.table(columns=columns, rows=asset_data, row_key='asset_tag', pagination=10).classes('w-full text-stone-800').props('flat bordered')

        # --- TAB: MAINTENANCE ---
        with ui.tab_panel(tab_maintenance):
            ui.label('Master Data Management').classes('text-2xl text-stone-800 font-light mb-6')

            with ui.grid(columns=2).classes('w-full gap-6'):
                # --------------------- CATEGORIES ---------------------
                with ui.card().classes('w-full h-full bg-white border border-stone-200 shadow-none rounded-sm p-6 justify-between'):
                    ui.label('Asset Categories').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-4 w-full')
                    
                    cat_cols = [
                        {'name': 'name', 'label': 'Category Name', 'field': 'name', 'align': 'left'},
                        {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'}
                    ]
                    cat_table = ui.table(columns=cat_cols, rows=[], row_key='id', pagination=5).classes('w-full text-stone-800').props('flat bordered dense')
                    
                    cat_table.add_slot('body-cell-actions', '''
                        <q-td :props="props">
                            <q-btn flat dense icon="edit" color="primary" @click="() => $parent.$emit('edit', props.row)" />
                            <q-btn flat dense icon="delete" color="negative" @click="() => $parent.$emit('delete', props.row)" />
                        </q-td>
                    ''')

                    def load_categories():
                        try:
                            cat_table.rows = supabase.table('categories').select('*').order('id').execute().data
                        except Exception:
                            pass
                    
                    def del_cat(row):
                        supabase.table('categories').delete().eq('id', row['id']).execute()
                        load_categories()
                        ui.notify('Deleted Category', type='warning')
                        
                    def edit_cat(row):
                        with ui.dialog() as d, ui.card().classes('p-6 min-w-[300px]'):
                            ui.label('Edit Category').classes('text-lg font-bold mb-4')
                            n = ui.input('Name', value=row['name']).classes('w-full mb-4')
                            def save():
                                supabase.table('categories').update({'name': n.value}).eq('id', row['id']).execute()
                                load_categories()
                                d.close()
                                ui.notify('Saved', type='positive')
                            ui.button('Save', on_click=save).classes('w-full bg-[#7F0019] text-white').props('unelevated')
                        d.open()
                        
                    cat_table.on('delete', lambda msg: del_cat(msg.args))
                    cat_table.on('edit', lambda msg: edit_cat(msg.args))
                    load_categories()

                    with ui.row().classes('w-full mt-4 items-center gap-2 flex-nowrap'):
                        new_cat_name = ui.input('New Category').props('outlined dense').classes('flex-1 min-w-[100px]')
                        def add_cat():
                            if new_cat_name.value:
                                supabase.table('categories').insert({'name': new_cat_name.value}).execute()
                                load_categories()
                                new_cat_name.value = ''
                                ui.notify('Added Category', type='positive')
                        ui.button(icon='add', on_click=add_cat).classes('bg-[#7F0019] text-white').props('unelevated round dense')

                # --------------------- LOCATIONS ---------------------
                with ui.card().classes('w-full h-full bg-white border border-stone-200 shadow-none rounded-sm p-6 justify-between'):
                    ui.label('Asset Locations').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-4 w-full')
                    
                    loc_cols = [
                        {'name': 'name', 'label': 'Location Name', 'field': 'name', 'align': 'left'},
                        {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'}
                    ]
                    loc_table = ui.table(columns=loc_cols, rows=[], row_key='id', pagination=5).classes('w-full text-stone-800').props('flat bordered dense')
                    loc_table.add_slot('body-cell-actions', '''
                        <q-td :props="props">
                            <q-btn flat dense icon="edit" color="primary" @click="() => $parent.$emit('edit', props.row)" />
                            <q-btn flat dense icon="delete" color="negative" @click="() => $parent.$emit('delete', props.row)" />
                        </q-td>
                    ''')

                    def load_locations():
                        try:
                            loc_table.rows = supabase.table('locations').select('*').order('id').execute().data
                        except Exception:
                            pass

                    def del_loc(row):
                        supabase.table('locations').delete().eq('id', row['id']).execute()
                        load_locations()
                        ui.notify('Deleted Location', type='warning')
                        
                    def edit_loc(row):
                        with ui.dialog() as d, ui.card().classes('p-6 min-w-[300px]'):
                            ui.label('Edit Location').classes('text-lg font-bold mb-4')
                            n = ui.input('Name', value=row['name']).classes('w-full mb-4')
                            def save():
                                supabase.table('locations').update({'name': n.value}).eq('id', row['id']).execute()
                                load_locations()
                                d.close()
                                ui.notify('Saved', type='positive')
                            ui.button('Save', on_click=save).classes('w-full bg-[#7F0019] text-white').props('unelevated')
                        d.open()
                        
                    loc_table.on('delete', lambda msg: del_loc(msg.args))
                    loc_table.on('edit', lambda msg: edit_loc(msg.args))
                    load_locations()

                    with ui.row().classes('w-full mt-4 items-center gap-2 flex-nowrap'):
                        new_loc_name = ui.input('New Location').props('outlined dense').classes('flex-1 min-w-[100px]')
                        def add_loc():
                            if new_loc_name.value:
                                supabase.table('locations').insert({'name': new_loc_name.value}).execute()
                                load_locations()
                                new_loc_name.value = ''
                                ui.notify('Added Location', type='positive')
                        ui.button(icon='add', on_click=add_loc).classes('bg-[#7F0019] text-white').props('unelevated round dense')

            with ui.row().classes('w-full mt-6'):
                # --------------------- DEPRECIATION RATES ---------------------
                with ui.card().classes('w-full bg-white border border-stone-200 shadow-none rounded-sm p-6'):
                    ui.label('Depreciation Rates').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-4 w-full')
                    
                    dep_msg = ui.label('Connecting...').classes('text-sm text-stone-500 mb-2')
                    
                    dep_cols = [
                        {'name': 'rate_name', 'label': 'Rate Name', 'field': 'rate_name', 'align': 'left'},
                        {'name': 'percentage', 'label': 'Percentage (%)', 'field': 'percentage', 'align': 'right'},
                        {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'}
                    ]
                    dep_table = ui.table(columns=dep_cols, rows=[], row_key='id', pagination=5).classes('w-full text-stone-800').props('flat bordered dense')
                    dep_table.add_slot('body-cell-actions', '''
                        <q-td :props="props">
                            <q-btn flat dense icon="edit" color="primary" @click="() => $parent.$emit('edit', props.row)" />
                            <q-btn flat dense icon="delete" color="negative" @click="() => $parent.$emit('delete', props.row)" />
                        </q-td>
                    ''')

                    def load_dep():
                        try:
                            dep_table.rows = supabase.table('depreciation_rates').select('*').order('id').execute().data
                            dep_msg.set_text('')
                        except Exception as e:
                            dep_msg.set_text('Note: Table "depreciation_rates" missing or schema mismatch (needs: id, rate_name, percentage).')
                            dep_msg.classes('text-red-500')
                            
                    def del_dep(row):
                        supabase.table('depreciation_rates').delete().eq('id', row['id']).execute()
                        load_dep()
                        ui.notify('Deleted Rate', type='warning')
                        
                    def edit_dep(row):
                        with ui.dialog() as d, ui.card().classes('p-6 min-w-[300px]'):
                            ui.label('Edit Rate').classes('text-lg font-bold mb-4')
                            n = ui.input('Rate Name', value=row['rate_name']).classes('w-full mb-2')
                            p = ui.number('Percentage', value=row['percentage']).classes('w-full mb-4')
                            def save():
                                supabase.table('depreciation_rates').update({'rate_name': n.value, 'percentage': p.value}).eq('id', row['id']).execute()
                                load_dep()
                                d.close()
                                ui.notify('Saved', type='positive')
                            ui.button('Save', on_click=save).classes('w-full bg-[#7F0019] text-white').props('unelevated')
                        d.open()

                    dep_table.on('delete', lambda msg: del_dep(msg.args))
                    dep_table.on('edit', lambda msg: edit_dep(msg.args))
                    load_dep()

                    with ui.row().classes('w-full mt-4 items-center gap-2 flex-nowrap'):
                        new_dep_name = ui.input('New Rate Name').props('outlined dense').classes('flex-1')
                        new_dep_pct = ui.number('Rate (%)', value=10.0).props('outlined dense').classes('w-24')
                        def add_dep():
                            if new_dep_name.value:
                                try:
                                    supabase.table('depreciation_rates').insert({'rate_name': new_dep_name.value, 'percentage': new_dep_pct.value}).execute()
                                    load_dep()
                                    new_dep_name.value = ''
                                    ui.notify('Added Rate', type='positive')
                                except Exception as e:
                                    ui.notify(f"Could not save: {e}", type="negative")
                        ui.button(icon='add', on_click=add_dep).classes('bg-[#7F0019] text-white').props('unelevated round dense')

# --- RUN THE APP ---
port = int(os.environ.get("PORT", 8080))
ui.run(title="Asset App", host="0.0.0.0", port=port)