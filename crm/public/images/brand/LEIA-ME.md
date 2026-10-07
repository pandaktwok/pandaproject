# PandaProject — Kit de marca

Gerado a partir da logo do panda com coroa. Tudo está organizado por uso.

## O que tem em cada pasta

| Pasta | Conteúdo | Quando usar |
|---|---|---|
| `01-logo-png` | Logo sozinha em 256, 512 e 1024 px, em 5 versões | Documentos, slides, qualquer tela |
| `02-logo-com-nome` | Logo + "PandaProject", horizontal e vertical, 4 cores, com e sem fundo | Cabeçalho do site, e-mail, propostas, contratos |
| `03-icones` | Favicon, ícones de app (iOS, Android, PWA), tiles do Windows, extensão | Site, sistema, celular |
| `04-redes-sociais` | Avatares, capas (X, LinkedIn, Facebook, YouTube) e imagem de compartilhamento | Redes sociais e link preview |
| `05-vetor` | SVG preto, branco e colorido | Impressão grande, plotter, camiseta, adesivo |

## Qual versão da logo usar

- **`logo-cores-transparente`**: fundo branco ou claro. O miolo do rosto fica transparente.
- **`logo-miolo-branco`**: fundo de qualquer cor média ou clara (o rosto fica branco).
- **`logo-fundo-escuro`**: fundo escuro. Tem um contorno claro fino para não sumir.
- **`logo-preto`**: uma cor só, fundo claro (carimbo, fax, bordado, papel timbrado simples).
- **`logo-branco`**: uma cor só, fundo escuro ou foto.

## Cores da marca

| Nome | Hex | Uso |
|---|---|---|
| Tinta | `#1C1C1C` | Fundos escuros, texto, tiles dos ícones |
| Grafite | `#3B3B3B` | Elementos secundários |
| Prata | `#B1B1B1` | Detalhes, bordas |
| Névoa | `#EDEDED` | Contorno da logo em fundo escuro |
| Papel | `#F6F4EF` | Fundo claro das capas |
| Branco | `#FFFFFF` | Fundo claro |

Fonte do nome: **Poppins** (Panda em Bold, Project em Light).

## Regras rápidas

- Deixe ao redor da logo um respiro de pelo menos 1/8 da largura dela.
- Tamanho mínimo da logo completa: 32 px de largura. Abaixo disso, use `icone-simplificado-16/32/48.png` (só o rosto, sem coroa).
- Não estique, não gire e não troque as cores da logo.

## Como colocar no site

Copie os arquivos de `03-icones` para a raiz do site e cole no `<head>`:

```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/icone-32.png">
<link rel="apple-touch-icon" href="/apple-touch-icon-180.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#1C1C1C">
<meta property="og:image" content="https://SEU-DOMINIO/og-image-compartilhamento-1200x630-escuro.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
```

Se preferir o favicon mais nítido em 16 px, use `favicon-simplificado.ico` no lugar de `favicon.ico`.

## Limites que você deve saber

- A imagem original tem 1024 px. Por isso os PNGs vão até 1024 px (as capas e lockups são montados em tamanho maior, mas a logo dentro deles não passa de 1024).
- Para qualquer coisa grande ou impressa, use os SVGs. O `logo-preto.svg` e o `logo-branco.svg` são fiéis ao desenho. O `logo-colorido.svg` é uma vetorização com os tons simplificados: perde um pouco do brilho metálico do original.
- Se você tiver a logo original em resolução maior (4000 px ou mais), me passe que eu refaço o kit com ela e o resultado fica melhor.
- Os arquivos `.ico` e os ícones pequenos (16 e 24 px) são menos detalhados por natureza.
- Antes de usar como marca comercial, vale registrar no INPI e conferir se a imagem não se parece com marcas já existentes.
