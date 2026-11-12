from flask import Flask, render_template, request
import sqlite3
import requests
import os

app = Flask(__name__)

STORE_ID = "915313"
ACCESS_TOKEN = "1ae3097bb3662f6318245a4c58c369bd146fda2f"

headers = {
    'Authentication': f'bearer {ACCESS_TOKEN}',
    'User-Agent': 'BLG ONLINE (sbalaguer06@gmail.com)'
}

LOGO_URL = "https://acdn-us.mitiendanube.com/stores/915/313/themes/common/logo-5398684041913048-1793922327-89d247ddac8140bcca2baf3612eed23e1793922327-640-0.webp"

def inicializar_base_de_datos():
    conexion = sqlite3.connect('blg_catalogo.db')
    cursor = conexion.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS categorias (id TEXT PRIMARY KEY, nombre TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id TEXT PRIMARY KEY, 
            sku TEXT, 
            nombre TEXT, 
            descripcion TEXT, 
            precio TEXT, 
            stock INTEGER, 
            imagen TEXT, 
            categoria_id TEXT
        )
    ''')
    conexion.commit()
    conexion.close()

def sincronizar_desde_tiendanube():
    conexion = sqlite3.connect('blg_catalogo.db')
    cursor = conexion.cursor()
    
    url_cats = f"https://api.tiendanube.com/v1/{STORE_ID}/categories"
    res_cats = requests.get(url_cats, headers=headers)
    if res_cats.status_code == 200:
        for cat in res_cats.json():
            cat_id = str(cat.get('id'))
            nombre = cat.get('name', {})
            cat_nombre = nombre.get('es') if isinstance(nombre, dict) else str(nombre)
            cursor.execute('INSERT OR REPLACE INTO categorias (id, nombre) VALUES (?, ?)', (cat_id, cat_nombre))
            
    pagina = 1
    while True:
        url_prods = f"https://api.tiendanube.com/v1/{STORE_ID}/products?per_page=200&page={pagina}"
        res_prods = requests.get(url_prods, headers=headers)
        if res_prods.status_code != 200:
            break
        prods = res_prods.json()
        if not prods:
            break
            
        for p in prods:
            pid = str(p.get('id'))
            nom = p.get('name', {})
            nombre = nom.get('es') if isinstance(nom, dict) else str(nom)
            
            desc = p.get('description', {})
            descripcion = desc.get('es') if isinstance(desc, dict) else str(desc)
            if not descripcion:
                descripcion = "Sin descripción detallada para este producto."
            
            vars = p.get('variants', [{}])
            variante = vars[0] if vars else {}
            precio = variante.get('price', 'Consultar')
            if not precio or precio == 'None':
                precio = 'Consultar'
                
            stock = variante.get('stock', 0)
            if stock is None:
                stock = 0
            sku = variante.get('sku', '') or 'SIN-SKU'
            
            imgs = p.get('images', [])
            img = imgs[0].get('src', '') if imgs else ''
            
            p_cats = p.get('categories', [])
            cid = str(p_cats[0].get('id')) if p_cats else 'sin_categoria'
            
            cursor.execute('''
                INSERT OR REPLACE INTO productos (id, sku, nombre, descripcion, precio, stock, imagen, categoria_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pid, sku, nombre, descripcion, str(precio), stock, img, cid))
            
        pagina += 1

    cursor.execute("INSERT OR IGNORE INTO categorias (id, nombre) VALUES ('sin_categoria', 'General')")
    conexion.commit()
    conexion.close()

@app.route('/')
def portada():
    return render_template('portada.html', logo_url=LOGO_URL)

@app.route('/catalogo')
def index():
    con = sqlite3.connect('blg_catalogo.db')
    cur = con.cursor()
    cur.execute("""
        SELECT DISTINCT c.id, c.nombre 
        FROM categorias c 
        JOIN productos p ON c.id = p.categoria_id
    """)
    cats = cur.fetchall()
    con.close()
    return render_template('index.html', categorias=cats, logo_url=LOGO_URL)

@app.route('/categoria/<cid>')
def categoria(cid):
    con = sqlite3.connect('blg_catalogo.db')
    cur = con.cursor()
    cur.execute("SELECT nombre FROM categorias WHERE id = ?", (cid,))
    r = cur.fetchone()
    nom = r[0] if r else "Productos"
    cur.execute("SELECT id, sku, nombre, precio, stock, imagen FROM productos WHERE categoria_id = ?", (cid,))
    prods = cur.fetchall()
    con.close()
    return render_template('categoria.html', nombre_cat=nom, productos=prods, logo_url=LOGO_URL)

@app.route('/buscar')
def buscar():
    query = request.args.get('q', '').strip()
    con = sqlite3.connect('blg_catalogo.db')
    cur = con.cursor()
    cur.execute("SELECT id, sku, nombre, precio, stock, imagen FROM productos WHERE nombre LIKE ? OR sku LIKE ?", ('%' + query + '%', '%' + query + '%'))
    prods = cur.fetchall()
    con.close()
    return render_template('categoria.html', nombre_cat=f"Resultados para: '{query}'", productos=prods, logo_url=LOGO_URL)

@app.route('/producto/<pid>')
def producto_detalle(pid):
    con = sqlite3.connect('blg_catalogo.db')
    cur = con.cursor()
    cur.execute("SELECT id, sku, nombre, descripcion, precio, stock, imagen FROM productos WHERE id = ?", (pid,))
    p = cur.fetchone()
    con.close()
    if not p:
        return "Producto no encontrado", 404
    return render_template('producto.html', producto=p, logo_url=LOGO_URL)
@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def sw():
    return app.send_static_file('sw.js')
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    inicializar_base_de_datos()
    sincronizar_desde_tiendanube()
    app.run(host='0.0.0.0', port=port)