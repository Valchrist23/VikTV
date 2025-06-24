import { addonBuilder } from 'stremio-addon-sdk';
import fetch from 'node-fetch';

const builder = new addonBuilder({
  id: 'org.tuusuario.nostalgiamovies',
  version: '1.0.0',
  name: 'Nostalgia Movies',
  description: 'Addon que muestra películas clásicas desde Internet Archive usando JSON de GitHub',
  catalogs: [
    {
      type: 'movie',
      id: 'peliculas-archive',
      name: 'Películas Nostalgia'
    }
  ],
  resources: ['catalog', 'stream'],
  types: ['movie'],
  idPrefixes: ['']
});

// 🌐 Cambia esta URL por la de tu archivo en GitHub
const jsonUrl = 'https://raw.githubusercontent.com/Valchrist23/VikTV/master/nostalgia.json';

// 📚 Catálogo
builder.defineCatalogHandler(() => {
  return fetch(jsonUrl)
    .then(res => res.json())
    .then(peliculas => {
      const metas = peliculas.map(pelicula => ({
        id: pelicula.id,
        name: pelicula.title,
        type: 'movie',
        poster: pelicula.poster
      }));
      return { metas };
    })
    .catch(err => {
      console.error('Error al obtener catálogo:', err);
      return { metas: [] };
    });
});

// 🎥 Stream
builder.defineStreamHandler(({ id }) => {
  return fetch(jsonUrl)
    .then(res => res.json())
    .then(peliculas => {
      const match = peliculas.find(p => p.id === id);
      if (match && match.url) {
        return {
          streams: [
            {
              title: match.title,
              url: match.url
            }
          ]
        };
      } else {
        return { streams: [] };
      }
    })
    .catch(err => {
      console.error('Error al obtener stream:', err);
      return { streams: [] };
    });
});

export const addon = builder.getInterface();
