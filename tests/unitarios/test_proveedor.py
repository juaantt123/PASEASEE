import pytest
from fastapi.testclient import TestClient

PRODUCTO = {'nombre': 'Producto proveedor', 'categoria': 'otros', 'precio': 5, 'stock': 3}


def test_productos_solo_del_proveedor(servicio):
    modulo, cliente = servicio('Merchandising')
    modulo.app.dependency_overrides[modulo.exigir_proveedor] = lambda: {'id': 101, 'tipo': 'proveedor'}
    with cliente:
        creado = cliente.post('/api/merchandising/proveedor/productos', json=PRODUCTO)
        assert creado.status_code == 201, creado.text
        identificador = creado.json()['id']
        assert [p['id'] for p in cliente.get('/api/merchandising/proveedor/productos').json()] == [identificador]
        modulo.app.dependency_overrides[modulo.exigir_proveedor] = lambda: {'id': 102, 'tipo': 'proveedor'}
        assert cliente.get('/api/merchandising/proveedor/productos').json() == []
        assert cliente.put(f'/api/merchandising/proveedor/productos/{identificador}', json=PRODUCTO).status_code == 403
        assert cliente.delete(f'/api/merchandising/proveedor/productos/{identificador}').status_code == 403
        modulo.app.dependency_overrides[modulo.exigir_proveedor] = lambda: {'id': 101, 'tipo': 'proveedor'}
        assert cliente.put(f'/api/merchandising/proveedor/productos/{identificador}', json={**PRODUCTO, 'stock': 7}).json()['stock'] == 7
        assert cliente.delete(f'/api/merchandising/proveedor/productos/{identificador}').status_code == 204


def test_registro_no_asigna_proveedor(servicio):
    _, cliente = servicio('Usuarios')
    with cliente:
        respuesta = cliente.post('/api/usuarios', json={
            'nombre': 'P', 'apellidos': 'P', 'email': 'proveedor@example.test',
            'password': 'Prueba1234', 'tipo': 'proveedor'
        })
        assert respuesta.status_code == 400


def test_acceso_sin_sesion_al_inventario(servicio):
    _, cliente = servicio('Merchandising')
    with cliente:
        assert cliente.get('/api/merchandising/proveedor/productos').status_code == 401
