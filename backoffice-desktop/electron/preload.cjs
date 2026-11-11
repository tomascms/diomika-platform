/**
 * Ponte mínima entre a página e o processo principal. A página não tem acesso ao sistema de ficheiros: só pode pedir
 * para gravar uma etiqueta, e quem decide onde gravar é o diálogo «Guardar como» do sistema.
 */
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('diomikaDesktop', {
  saveLabel: (fileName, bytes) => ipcRenderer.invoke('save-label', { fileName, bytes }),
})
