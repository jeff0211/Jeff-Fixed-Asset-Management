from nicegui import ui
from supabase import create_client, Client
import os
import csv
import io
from datetime import date
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
    # Fetching more fields (id, raw category/location IDs, date) to support editing
    response = supabase.table("assets").select("*, categories(name), locations(name)").order("id", desc=True).execute()
    assets = []
    for row in response.data:
        assets.append({
            'id': row['id'],
            'name': row['name'],
            'category': row['categories']['name'] if row['categories'] else 'N/A',
            'category_id': row['category_id'],
            'location': row['locations']['name'] if row['locations'] else 'N/A',
            'location_id': row['location_id'],
            'status': row['status'],
            'price_raw': row['purchase_cost'],
            'price': f"RM {row['purchase_cost']:,.2f}",
            'quantity': row.get('quantity', 1),
            'unit_cost': row.get('unit_cost', 0.0),
            'purchase_date': row['purchase_date'],
            'purchase_year': row.get('purchase_year'),
            'depreciation_rate': row.get('depreciation_rate', 0.0), # Ensure we handle missing depreciation rate
            'remarks': row.get('remarks', '')
        })
    return assets

# --- UI LAYOUT ---

# Header: Crisp white background, thin border, zero shadow
with ui.header().classes('bg-[#8b6854] border-b border-stone-200 text-white items-center justify-between px-8 py-3 shadow-none'):
    # A simple, elegant title
    ui.label('Fixed Assets Module Demo').classes('text-xl tracking-wide font-light')
    
    # "Flat" button style for logout to keep it minimal
    ui.button('Sign Out', color='accent').props('flat').classes('text-sm tracking-wider font-light text-white')

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
            
            # Helper functions to grab the live menus from Supabase
            def get_cat_options():
                try: return {row['id']: row['name'] for row in supabase.table('categories').select('*').execute().data}
                except Exception: return {}

            def get_loc_options():
                try: return {row['id']: row['name'] for row in supabase.table('locations').select('*').execute().data}
                except Exception: return {}

            def get_rate_options():
                try: return {row['percentage']: row['rate_name'] for row in supabase.table('depreciation_rates').select('*').execute().data}
                except Exception: return {}

            # Form Card: Pure white, thin border, sharp corners
            with ui.card().classes('w-full max-w-2xl bg-white border border-stone-200 shadow-none rounded-sm p-8 mx-auto'):
                ui.label('New Asset Details').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-6 w-full')
                
                # Top Row: Text Inputs
                name = ui.input('Asset Description').classes('w-full mb-4').props('outlined dense')
                remarks = ui.input('Remarks').classes('w-full mb-4').props('outlined dense')
                
                # Middle Row: Foreign Key Dropdowns (Categories & Locations)
                with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                    cat_select = ui.select(get_cat_options(), label='Category').classes('w-1/2').props('outlined dense')
                    loc_select = ui.select(get_loc_options(), label='Location').classes('w-1/2').props('outlined dense')

                # Cost Row: Qty, Unit Cost, and Total Purchase Cost
                def update_total_cost():
                    try:
                        q = float(qty.value) if qty.value else 0.0
                        u = float(unit_cost_input.value) if unit_cost_input.value else 0.0
                        price.value = round(q * u, 2)
                    except (ValueError, TypeError):
                        pass

                with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                    qty = ui.number('Qty', value=1, min=1, format='%d', on_change=update_total_cost).classes('w-1/4').props('outlined dense')
                    unit_cost_input = ui.number('Unit Cost (RM)', value=0.0, format='%.2f', on_change=update_total_cost).classes('flex-1').props('outlined dense')
                    price = ui.number('Purchase Cost (RM)', format='%.2f').classes('flex-1').props('outlined dense')

                # Rate and Status Row
                with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                    rate_select = ui.select(get_rate_options(), label='Depreciation Rate', with_input=True).classes('w-1/2').props('outlined dense')
                    status = ui.select(['Active', 'Disposed'], value='Active', label='Status').classes('w-1/2').props('outlined dense')

                # Tiny refresh button so staff can sync the dropdowns if maintenance was updated
                with ui.row().classes('w-full justify-end mb-4'):
                    def refresh_dropdowns():
                        cat_select.options = get_cat_options()
                        cat_select.update()
                        loc_select.options = get_loc_options()
                        loc_select.update()
                        rate_select.options = get_rate_options()
                        rate_select.update()
                        ui.notify('Dropdowns synced with master data', type='info', position='top-right')
                    ui.button('↻ Sync Options', on_click=refresh_dropdowns).props('flat dense').classes('text-stone-400 text-xs tracking-wider')

                # The Save Logic
                def save_asset():
                    # 1. Validation Check
                    if not name.value or qty.value is None or unit_cost_input.value is None:
                        ui.notify('Please fill in the Asset Description, Quantity, and Unit Cost.', type='warning', position='top')
                        return
                    
                    try:
                        # 2. Push to Database
                        supabase.table('assets').insert({
                            'name': name.value,
                            'remarks': remarks.value,
                            'category_id': cat_select.value, # Foreign key link!
                            'location_id': loc_select.value, # Foreign key link!
                            'quantity': int(qty.value) if qty.value else 1,
                            'unit_cost': float(unit_cost_input.value) if unit_cost_input.value else 0.0,
                            'purchase_cost': float(price.value) if price.value else 0.0,
                            'depreciation_rate': float(rate_select.value) if rate_select.value else 0.0,
                            'purchase_date': purchase_date_input.value,
                            'purchase_year': int(purchase_year_input.value) if purchase_year_input.value else None,
                            'status': status.value
                        }).execute()
                        
                        ui.notify('Asset recorded successfully', position='top', type='positive')
                        
                        # 3. Clear the form for the next entry
                        name.value = ''
                        remarks.value = ''
                        qty.value = 1
                        unit_cost_input.value = 0.0
                        price.value = 0.0
                        cat_select.value = None
                        loc_select.value = None
                        rate_select.value = None
                        purchase_date_input.value = str(date.today())
                        purchase_year_input.value = date.today().year
                        
                    except Exception as e:
                        ui.notify(f'Database error: Please check your data or foreign keys. ({e})', type='negative')
                        
                # Primary Button
                ui.button('Save Record', on_click=save_asset).classes('w-full py-2 tracking-wide font-light bg-[#7F0019] text-white').props('unelevated')
                
        # --- TAB: DISPOSAL ---
        with ui.tab_panel(tab_disposal):

            # Helper functions to grab the live menus from Supabase
            def get_disp_cat_options():
                try: return {row['id']: row['name'] for row in supabase.table('categories').select('*').execute().data}
                except Exception: return {}

            def get_disp_loc_options():
                try: return {row['id']: row['name'] for row in supabase.table('locations').select('*').execute().data}
                except Exception: return {}



            # Form Card: Pure white, thin border, sharp corners
            with ui.card().classes('w-full max-w-2xl bg-white border border-stone-200 shadow-none rounded-sm p-8 mx-auto'):
                ui.label('Asset Disposal Details').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-6 w-full')

                # Top Row: Text Inputs
                disp_name = ui.input('Asset Description').classes('w-full mb-4').props('outlined dense')
                disp_remarks = ui.input('Remarks').classes('w-full mb-4').props('outlined dense')

                # Middle Row: Foreign Key Dropdowns (Categories & Locations)
                with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                    disp_cat_select = ui.select(get_disp_cat_options(), label='Category').classes('w-1/2').props('outlined dense')
                    disp_loc_select = ui.select(get_disp_loc_options(), label='Location').classes('w-1/2').props('outlined dense')

                # Sales/Cost Row: Sales Proceed, Qty, Unit Cost, and Total Disposal Cost
                def update_total_disp_cost():
                    try:
                        q = float(disp_qty.value) if disp_qty.value else 0.0
                        u = float(disp_unit_cost.value) if disp_unit_cost.value else 0.0
                        total_disp_cost.value = round(q * u, 2)
                    except (ValueError, TypeError):
                        pass

                with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                    disp_sales_proceed = ui.number('Sales Proceed (RM)', format='%.2f').classes('w-1/2').props('outlined dense')
                    disp_qty = ui.number('Quantity Disposed', value=1, min=1, format='%d', on_change=update_total_disp_cost).classes('w-1/4').props('outlined dense')
                    disp_unit_cost = ui.number('Cost per Unit', value=0.0, format='%.2f', on_change=update_total_disp_cost).classes('flex-1').props('outlined dense')

                with ui.row().classes('w-full mb-4'):
                    total_disp_cost = ui.number('Total Cost of Asset Disposed (RM)', value=0.0, format='%.2f').classes('w-full').props('outlined dense readonly')

                # Date Row: Disposal Date & Year of Disposal
                with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                    disp_year_input = ui.number('Year of Disposal', value=date.today().year, format='%d').classes('w-1/2').props('outlined dense readonly')

                    def update_disp_year_from_date():
                        try:
                            disp_year_input.value = int(disp_date_input.value[:4])
                        except (ValueError, TypeError):
                            pass

                    disp_date_input = ui.input('Date of Disposal', value=str(date.today()), on_change=lambda: update_disp_year_from_date()).classes('w-1/2').props('outlined dense')
                    with disp_date_input:
                        with ui.menu().props('no-parent-event') as disp_date_menu:
                            with ui.date().bind_value(disp_date_input) as disp_date_picker:
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=disp_date_menu.close).props('flat')
                        with disp_date_input.add_slot('append'):
                            ui.icon('edit_calendar').on('click', disp_date_menu.open).classes('cursor-pointer')

                # Tiny refresh button so staff can sync the dropdowns if maintenance was updated
                with ui.row().classes('w-full justify-end mb-4'):
                    def refresh_disp_dropdowns():
                        disp_cat_select.options = get_disp_cat_options()
                        disp_cat_select.update()
                        disp_loc_select.options = get_disp_loc_options()
                        disp_loc_select.update()
                        ui.notify('Dropdowns synced with master data', type='info', position='top-right')
                    ui.button('↻ Sync Options', on_click=refresh_disp_dropdowns).props('flat dense').classes('text-stone-400 text-xs tracking-wider')

                # The Save Logic
                def save_disposal():
                    # 1. Validation Check
                    if not disp_name.value or disp_qty.value is None or disp_unit_cost.value is None:
                        ui.notify('Please fill in the Asset Description, Qty Disposed, and Cost per Unit.', type='warning', position='top')
                        return

                    try:
                        # 2. Push to disposals table
                        supabase.table('disposals').insert({
                            'name': disp_name.value,
                            'remarks': disp_remarks.value,
                            'category_id': disp_cat_select.value,
                            'location_id': disp_loc_select.value,
                            'sales_proceed': float(disp_sales_proceed.value) if disp_sales_proceed.value else 0.0,
                            'quantity_disposed': int(disp_qty.value) if disp_qty.value else 1,
                            'unit_cost': float(disp_unit_cost.value) if disp_unit_cost.value else 0.0,
                            'total_disposal_cost': float(total_disp_cost.value) if total_disp_cost.value else 0.0,
                            'disposal_date': disp_date_input.value,
                            'disposal_year': int(disp_year_input.value) if disp_year_input.value else None,
                            'status': 'Disposed'
                        }).execute()



                        ui.notify(f'Disposal recorded successfully', position='top', type='positive')

                        # 4. Clear the form for the next entry
                        disp_name.value = ''
                        disp_remarks.value = ''
                        disp_sales_proceed.value = 0.0
                        disp_qty.value = 1
                        disp_unit_cost.value = 0.0
                        total_disp_cost.value = 0.0
                        disp_cat_select.value = None
                        disp_loc_select.value = None
                        disp_date_input.value = str(date.today())
                        disp_year_input.value = date.today().year

                    except Exception as e:
                        ui.notify(f'Database error: Please check your data or foreign keys. ({e})', type='negative')

                # Primary Button
                ui.button('Record Disposal', on_click=save_disposal).classes('w-full py-2 tracking-wide font-light bg-[#7F0019] text-white').props('unelevated')

        # --- TAB: REPORTS (Including Asset Register) ---
        with ui.tab_panel(tab_reports):
            
            # Header Row with Title and Export Button
            with ui.row().classes('w-full items-center justify-between mb-4 px-2'):
                ui.label('Comprehensive Asset Register').classes('text-xl text-stone-800 font-light')
                
                def export_csv():
                    data = get_assets()
                    output = io.StringIO()
                    writer = csv.writer(output)
                    writer.writerow(['Asset Description', 'Category', 'Location', 'Status', 'Purchase Cost'])
                    for row in data:
                        writer.writerow([row['name'], row['category'], row['location'], row['status'], row['price']])
                    ui.download(output.getvalue().encode('utf-8'), 'asset_register.csv')
                    ui.notify('Download started', type='positive')
                
                ui.button('Export to CSV', icon='download', on_click=export_csv).classes('text-sm tracking-wide bg-[#7F0019] text-white').props('unelevated')

            # Search Row: Muji-style search bar
            with ui.row().classes('w-full mb-4 px-2'):
                search_input = ui.input(placeholder='Search assets by name, category, or status...').classes('w-full').props('outlined dense clearable')
                search_input.on('input', lambda: asset_table.update()) # Force table update on search

            # The Table: .props('flat bordered') removes the shadow and adds a crisp line
            columns = [
                {'name': 'name', 'label': 'Description', 'field': 'name', 'align': 'left', 'sortable': True},
                {'name': 'category', 'label': 'Category', 'field': 'category', 'align': 'left', 'sortable': True},
                {'name': 'location', 'label': 'Location', 'field': 'location', 'align': 'left', 'sortable': True},
                {'name': 'status', 'label': 'Status', 'field': 'status', 'align': 'center', 'sortable': True},
                {'name': 'price', 'label': 'Purchase Cost', 'field': 'price', 'align': 'right', 'sortable': True},
                {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'},
            ]
            
            asset_data = get_assets()
            asset_table = ui.table(columns=columns, rows=asset_data, row_key='id', pagination=10).classes('w-full text-stone-800').props('flat bordered')
            asset_table.bind_filter_from(search_input, 'value')

            # --- EDIT LOGIC ---
            asset_table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn flat dense icon="edit" color="primary" @click="() => $parent.$emit('edit', props.row)" />
                </q-td>
            ''')

            def refresh_reports():
                asset_table.rows = get_assets()
                asset_table.update()

            def edit_asset(row):
                try:
                    # Pre-load dropdown options before building the dialog
                    try:
                        cat_opts = {r['id']: r['name'] for r in supabase.table('categories').select('*').execute().data}
                    except Exception:
                        cat_opts = {}
                    try:
                        loc_opts = {r['id']: r['name'] for r in supabase.table('locations').select('*').execute().data}
                    except Exception:
                        loc_opts = {}
                    try:
                        rate_opts = {r['percentage']: r['rate_name'] for r in supabase.table('depreciation_rates').select('*').execute().data}
                    except Exception:
                        rate_opts = {}

                    # Build the Edit Dialog — mirrors the Add Assets tab exactly
                    with ui.dialog() as d, ui.card().classes('w-full max-w-2xl bg-white border border-stone-200 shadow-none rounded-sm p-8 mx-auto'):
                        ui.label(f'Edit Asset: {row.get("name", "")}').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-6 w-full')

                        # Top Row: Text Inputs
                        e_name = ui.input('Asset Description', value=row.get('name', '')).classes('w-full mb-4').props('outlined dense')
                        e_remarks = ui.input('Remarks', value=row.get('remarks', '')).classes('w-full mb-4').props('outlined dense')

                        # Middle Row: Foreign Key Dropdowns (Categories & Locations)
                        with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                            cat_val = row.get('category_id')
                            loc_val = row.get('location_id')
                            e_cat = ui.select(cat_opts, label='Category', value=cat_val if cat_val in cat_opts else None).classes('w-1/2').props('outlined dense')
                            e_loc = ui.select(loc_opts, label='Location', value=loc_val if loc_val in loc_opts else None).classes('w-1/2').props('outlined dense')

                        # Cost Row: Qty, Unit Cost, and Total Purchase Cost
                        def update_edit_total_cost():
                            try:
                                q = float(e_qty.value) if e_qty.value else 0.0
                                u = float(e_unit_cost.value) if e_unit_cost.value else 0.0
                                e_price.value = round(q * u, 2)
                            except (ValueError, TypeError):
                                pass

                        with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                            e_qty = ui.number('Qty', value=row.get('quantity', 1), min=1, format='%d', on_change=update_edit_total_cost).classes('w-1/4').props('outlined dense')
                            e_unit_cost = ui.number('Unit Cost (RM)', value=row.get('unit_cost', 0.0), format='%.2f', on_change=update_edit_total_cost).classes('flex-1').props('outlined dense')
                            e_price = ui.number('Purchase Cost (RM)', value=row.get('price_raw'), format='%.2f').classes('flex-1').props('outlined dense')

                        # Rate and Status Row
                        with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                            rate_val = row.get('depreciation_rate', 0.0)
                            e_rate = ui.select(rate_opts, label='Depreciation Rate', value=rate_val if rate_val in rate_opts else None, with_input=True).classes('w-1/2').props('outlined dense')
                            e_status = ui.select(['Active', 'Disposed'], value=row.get('status', 'Active'), label='Status').classes('w-1/2').props('outlined dense')

                        # Date Row: Purchase Date & Year of Purchase
                        with ui.row().classes('w-full gap-4 mb-4 flex-nowrap'):
                            existing_year = row.get('purchase_year') or date.today().year
                            try:
                                existing_year = int(row.get('purchase_date', '')[:4])
                            except (ValueError, TypeError):
                                pass
                            e_purchase_year = ui.number('Year of Purchase', value=existing_year, format='%d').classes('w-1/2').props('outlined dense readonly')

                            def update_edit_year_from_date():
                                try:
                                    e_purchase_year.value = int(e_purchase_date.value[:4])
                                except (ValueError, TypeError):
                                    pass

                            e_purchase_date = ui.input('Date of Purchase', value=row.get('purchase_date', str(date.today())), on_change=lambda: update_edit_year_from_date()).classes('w-1/2').props('outlined dense')
                            with e_purchase_date:
                                with ui.menu().props('no-parent-event') as e_date_menu:
                                    with ui.date().bind_value(e_purchase_date) as e_date_picker:
                                        with ui.row().classes('justify-end'):
                                            ui.button('Close', on_click=e_date_menu.close).props('flat')
                                with e_purchase_date.add_slot('append'):
                                    ui.icon('edit_calendar').on('click', e_date_menu.open).classes('cursor-pointer')

                        # Sync Options button to refresh dropdowns
                        with ui.row().classes('w-full justify-end mb-4'):
                            def refresh_edit_dropdowns():
                                try:
                                    e_cat.options = {r['id']: r['name'] for r in supabase.table('categories').select('*').execute().data}
                                    e_cat.update()
                                    e_loc.options = {r['id']: r['name'] for r in supabase.table('locations').select('*').execute().data}
                                    e_loc.update()
                                    e_rate.options = {r['percentage']: r['rate_name'] for r in supabase.table('depreciation_rates').select('*').execute().data}
                                    e_rate.update()
                                    ui.notify('Dropdowns synced with master data', type='info', position='top-right')
                                except Exception:
                                    ui.notify('Failed to sync dropdowns', type='warning')
                            ui.button('↻ Sync Options', on_click=refresh_edit_dropdowns).props('flat dense').classes('text-stone-400 text-xs tracking-wider')

                        # The Update Logic
                        def save_changes():
                            # 1. Validation Check
                            if not e_name.value or e_qty.value is None or e_unit_cost.value is None:
                                ui.notify('Please fill in the Asset Description, Quantity, and Unit Cost.', type='warning', position='top')
                                return
                            try:
                                # 2. Push update to Database
                                supabase.table('assets').update({
                                    'name': e_name.value,
                                    'remarks': e_remarks.value,
                                    'category_id': e_cat.value,
                                    'location_id': e_loc.value,
                                    'quantity': int(e_qty.value) if e_qty.value else 1,
                                    'unit_cost': float(e_unit_cost.value) if e_unit_cost.value else 0.0,
                                    'purchase_cost': float(e_price.value) if e_price.value else 0.0,
                                    'depreciation_rate': float(e_rate.value) if e_rate.value else 0.0,
                                    'purchase_date': e_purchase_date.value,
                                    'purchase_year': int(e_purchase_year.value) if e_purchase_year.value else None,
                                    'status': e_status.value
                                }).eq('id', row['id']).execute()

                                ui.notify('Asset updated successfully', position='top', type='positive')
                                refresh_reports()
                                d.close()
                            except Exception as e:
                                ui.notify(f'Database error: Please check your data or foreign keys. ({e})', type='negative')

                        # Delete Logic
                        def delete_record():
                            with ui.dialog() as confirm_dialog, ui.card().classes('p-6 bg-white border border-stone-200 shadow-none rounded-sm'):
                                ui.label('Confirm Deletion').classes('text-lg tracking-wide text-stone-800 border-b border-stone-100 pb-2 mb-4 w-full')
                                ui.label(f'Are you sure you want to delete "{row.get("name", "this asset")}"? This action cannot be undone.').classes('text-stone-600 mb-6')
                                with ui.row().classes('w-full gap-4 justify-end'):
                                    ui.button('Cancel', on_click=confirm_dialog.close).props('flat').classes('text-stone-500')
                                    def confirm_delete():
                                        try:
                                            supabase.table('assets').delete().eq('id', row['id']).execute()
                                            ui.notify('Record deleted successfully', type='positive', position='top')
                                            refresh_reports()
                                            confirm_dialog.close()
                                            d.close()
                                        except Exception as e:
                                            ui.notify(f'Delete error: {e}', type='negative')
                                    ui.button('Delete', on_click=confirm_delete).classes('bg-red-700 text-white').props('unelevated')
                            confirm_dialog.open()

                        # Action Buttons
                        ui.button('Update Record', on_click=save_changes).classes('w-full py-2 tracking-wide font-light bg-[#7F0019] text-white').props('unelevated')
                        ui.button('Delete Record', icon='delete', on_click=delete_record).classes('w-full py-2 mt-2 tracking-wide font-light text-red-700').props('flat')
                    d.open()

                except Exception as e:
                    ui.notify(f'Could not open edit dialog: {e}', type='negative')

            asset_table.on('edit', lambda msg: edit_asset(msg.args))

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
                    cat_table = ui.table(columns=cat_cols, rows=[], row_key='id', pagination=5).classes('w-full text-stone-800').props('flat bordered dense').style('height: 260px')
                    
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
                    loc_table = ui.table(columns=loc_cols, rows=[], row_key='id', pagination=5).classes('w-full text-stone-800').props('flat bordered dense').style('height: 260px')
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
                    
                    dep_msg = ui.label('Connecting...').classes('text-sm text-stone-500')
                    
                    dep_cols = [
                        {'name': 'rate_name', 'label': 'Rate Name', 'field': 'rate_name', 'align': 'left'},
                        {'name': 'percentage', 'label': 'Percentage (%)', 'field': 'percentage', 'align': 'center'},
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
                            dep_msg.set_visibility(False)
                        except Exception as e:
                            dep_msg.set_visibility(True)
                            dep_msg.set_text('Note: Table "depreciation_rates" missing or schema mismatch (needs: id, rate_name, percentage).')
                            dep_msg.classes('text-red-500 mb-2')
                            
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