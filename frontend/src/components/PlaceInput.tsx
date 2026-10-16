import { useId, useState, type KeyboardEvent } from "react";
import type { Place } from "../api/types";
import type { PlaceField } from "../domain/tripForm";
import { usePlaceSuggestions } from "../hooks/usePlaceSuggestions";

interface Props {
  label: string;
  value: PlaceField;
  onChange: (value: PlaceField) => void;
}

export function PlaceInput({ label, value, onChange }: Props) {
  const id = useId();
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const suggestions = usePlaceSuggestions(value.text, focused && !value.place);
  const open = focused && suggestions.length > 0;

  const choose = (place: Place) => {
    onChange({ text: place.name, place });
    setActiveIndex(-1);
  };

  const onKeyDown = (event: KeyboardEvent) => {
    if (!open) return;
    if (event.key === "ArrowDown") setActiveIndex((activeIndex + 1) % suggestions.length);
    else if (event.key === "ArrowUp") setActiveIndex((activeIndex - 1 + suggestions.length) % suggestions.length);
    else if (event.key === "Enter" && activeIndex >= 0) choose(suggestions[activeIndex]);
    else if (event.key === "Escape") setFocused(false);
    else return;
    event.preventDefault();
  };

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        role="combobox"
        aria-expanded={open}
        aria-controls={`${id}-options`}
        aria-activedescendant={activeIndex >= 0 ? `${id}-option-${activeIndex}` : undefined}
        aria-autocomplete="list"
        autoComplete="off"
        placeholder="City, address or place"
        value={value.text}
        onChange={(event) => {
          onChange({ text: event.target.value });
          setActiveIndex(-1);
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onKeyDown={onKeyDown}
      />
      {open && (
        <ul className="suggestions" id={`${id}-options`} role="listbox" aria-label={`${label} suggestions`}>
          {suggestions.map((place, index) => (
            <li
              key={`${place.lat},${place.lon}`}
              id={`${id}-option-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              // mousedown fires before the input's blur closes the list, so the choice still lands.
              onMouseDown={(event) => {
                event.preventDefault();
                choose(place);
              }}
            >
              {place.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
