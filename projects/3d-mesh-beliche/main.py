import trimesh
import numpy as np


# Função auxiliar para criar blocos equivalente ao 'draw_block' do Ruby
def draw_block(name, x, y, z, width, depth, height):
    # No trimesh, a caixa é gerada com o centro no ponto (0,0,0).
    # Precisamos deslocá-la para que o canto inferior esquerdo fique em (x, y, z)
    box = trimesh.creation.box(extents=[width, depth, height])

    # Matriz de translação para mover o bloco
    translation = trimesh.transformations.translation_matrix(
        [x + width / 2, y + depth / 2, z + height / 2]
    )
    box.apply_transform(translation)

    # Opcional: Adicionar metadados (nome)
    box.metadata["name"] = name
    return box


def main():
    # 1. Volume da Cama Principal (194,3 x 84 x 143 cm)
    cama = draw_block("Volume_Cama", 37.5, 0, 0, 194.3, 84.0, 143.0)

    # 2. Construção dos Degraus / Nichos
    degrau1 = draw_block("Degrau_1", 0, 0, 0, 36.0, 99.0, 32.5)
    degrau2 = draw_block("Degrau_2", 0, 20.0, 32.5, 36.0, 79.0, 32.5)
    degrau3 = draw_block("Degrau_3", 0, 40.0, 65.0, 36.0, 59.0, 32.5)
    degrau4 = draw_block("Degrau_4", 0, 60.0, 97.5, 36.0, 39.0, 32.5)

    # Combina todos os blocos em uma única malha 3D
    beliche = trimesh.util.concatenate([cama, degrau1, degrau2, degrau3, degrau4])

    # Exporta para os formatos desejados (Apenas com Python, sem SketchUp)
    beliche.export("beliche.stl")
    beliche.export("beliche.dae")
    # beliche.export("beliche.obj") # Outro formato popular suportado

    print("Volumetria da beliche gerada e exportada com sucesso!")


if __name__ == "__main__":
    main()
