import catalog from "../../../packages/shared/church-callings.json";

export type CallingCategory = {
  id: string;
  label: string;
  callings: string[];
};

export type CallingFocus = {
  callingCategory?: string;
  callingName?: string;
  customCallingName?: string;
  callingFocusEnabled: boolean;
};

export const OTHER_CALLING_LABEL = "Otro llamamiento";

export const callingCatalog = catalog as CallingCategory[];

export function allCallingNames() {
  return callingCatalog.flatMap((category) => category.callings);
}

export function categoryById(categoryId?: string) {
  return callingCatalog.find((category) => category.id === categoryId);
}

export function isOtherCalling(callingName?: string) {
  if (!callingName) return false;
  return callingName.toLowerCase().includes("otro");
}

export function resolvedCallingName(focus: CallingFocus) {
  if (!focus.callingFocusEnabled) return undefined;
  if (isOtherCalling(focus.callingName) && focus.customCallingName?.trim()) {
    return focus.customCallingName.trim();
  }
  return focus.callingName?.trim() || focus.customCallingName?.trim() || undefined;
}

export function callingCategoryLabel(categoryId?: string) {
  return categoryById(categoryId)?.label ?? categoryId;
}
