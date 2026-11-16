document.addEventListener('DOMContentLoaded', async () => {
    const catalogo = document.getElementById('catalogo-tienda');
    try {
        const respuesta = await fetch(`${API_TIENDA}/merchandising/disponibles`);
        if (!respuesta.ok) throw new Error('No se pudo consultar el catálogo.');
        const productos = await respuesta.json();
        catalogo.replaceChildren();
        if (!productos.length) {
            catalogo.textContent = 'No hay productos disponibles.';
            return;
        }
        for (const producto of productos) {
            const tarjeta = document.createElement('article');
            tarjeta.className = 'shop-card';
            const contenido = document.createElement('div');
            contenido.className = 'shop-card-content';
            const categoria = document.createElement('span');
            categoria.className = 'shop-category';
            categoria.textContent = producto.categoria;
            const nombre = document.createElement('h3');
            nombre.textContent = producto.nombre;
            const descripcion = document.createElement('p');
            descripcion.textContent = producto.descripcion || '';
            const pie = document.createElement('div');
            pie.className = 'shop-card-footer';
            const precio = document.createElement('span');
            precio.className = 'shop-price';
            precio.textContent = `${Number(producto.precio).toLocaleString('es-ES')} €`;
            const enlace = document.createElement('a');
            enlace.className = 'btn shop-buy-button';
            enlace.href = `comprar-producto.html?producto=${encodeURIComponent(producto.id)}`;
            enlace.textContent = 'Comprar';
            pie.append(precio, enlace);
            contenido.append(categoria, nombre, descripcion, pie);
            tarjeta.append(contenido);
            catalogo.append(tarjeta);
        }
    } catch (error) {
        catalogo.textContent = `No se pudo cargar la tienda: ${error.message}`;
    }
});
