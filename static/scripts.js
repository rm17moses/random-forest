document.addEventListener("alpine:init", () => {
  Alpine.data('prediction', () => {
    return {
      show: false,
      hide: false,


    }
  })
})