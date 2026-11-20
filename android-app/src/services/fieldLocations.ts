import { ApiClient, ApiError } from "./api";
import { store } from "./storage";
import type { FieldLocationInput, FieldLocationRequest, Visit } from "../types";
export const fieldOutboxKey = (scope: string) =>
  scope + "field-location-outbox";
export async function submitFieldLocations(
  api: ApiClient,
  scope: string,
  visit: Visit,
  input: FieldLocationInput,
) {
  const key = fieldOutboxKey(scope);
  const pending = await store.get<FieldLocationRequest>(key);
  const data = pending || {
    ...input,
    id: crypto.randomUUID(),
    expected_visit_version: visit.version,
  };
  if (!pending) await store.put(key, data);
  try {
    const result = await api.addFieldLocations(visit.id, data);
    await store.remove(key);
    return result.visit;
  } catch (error) {
    // A lost response must retry the same UUID; explicit rejection allows review
    // and a corrected request. The separate editable form draft remains intact.
    if (
      error instanceof ApiError &&
      [400, 401, 403, 404, 409, 422, 429, 503].includes(error.status)
    )
      await store.remove(key);
    throw error;
  }
}
