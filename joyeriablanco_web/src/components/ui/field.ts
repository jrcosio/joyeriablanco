/** Clases compartidas por los campos de formulario (DESIGN.md §Form Fields). */
export const campoContenedor = 'group flex flex-col gap-1.5'
export const campoEtiqueta =
  'label-md text-on-surface-variant group-focus-within:text-primary transition-colors'
export const campoCaja =
  'h-11 w-full bg-surface-container-low border border-on-surface/12 px-3 body-md ' +
  'text-on-surface placeholder:text-on-surface-variant/60 outline-none transition-colors ' +
  'data-[focused]:border-primary-container focus:border-primary-container ' +
  'data-[invalid]:border-danger group-data-[invalid]:border-danger ' +
  'data-[disabled]:opacity-50'
export const campoAyuda = 'body-sm text-on-surface-variant'
export const campoError = 'body-sm text-danger'
