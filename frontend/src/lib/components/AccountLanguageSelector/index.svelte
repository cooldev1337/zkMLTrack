<script>
  import { getLocale, setLocale } from '$lib/paraglide/runtime';
  import { m } from '$lib/paraglide/messages.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { Dialog, DialogContent } from '$lib/components/ui/dialog';
  import { LoaderCircle } from '@lucide/svelte';
  import usFlag from "$lib/assets/flags/us.png"
  import esFlag from "$lib/assets/flags/es.png"

  const noop = () => {};

  let submitting = $state("");
  let language = $state(getLocale());

  const changeToEn = () => {
    submitting = "en";
    language = "en";
    setLocale("en");
  }

  const changeToEs = () => {
    submitting = "es";
    language = "es";
    setLocale("es");
  }
</script>

<div class="flex flex-wrap gap-1">
  <Button
    value="en"
    variant={language == "en" ? "default" : "ghost"}
    onclick={language == "en" ? noop : changeToEn}
  >
    <img src={usFlag}/><span>&nbsp;{m.language_en()}</span>
  </Button>
  <Button
    value="es"
    variant={language == "es" ? "default" : "ghost"}
    onclick={language == "es" ? noop : changeToEs}
  >
    <img src={esFlag}/><span>&nbsp;{m.language_es()}</span>
  </Button>
</div>

<Dialog open={submitting}>
  <DialogContent class="flex items-center justify-center h-32 [&>button:last-child]:hidden" onInteractOutside={(e) => e.preventDefault()}>
    <LoaderCircle class="animate-spin w-16 h-16 text-gray-700 dark:text-gray-300" />
  </DialogContent>
</Dialog>