from __future__ import annotations
from typing import TypeVar, Generic, TYPE_CHECKING
import logging

from pywm import PyWMViewDownstreamState, PyWMWidgetDownstreamState, PyWMDownstreamState, PyWMWidget

from .config import configured_value

if TYPE_CHECKING:
    from .layout import Layout

logger = logging.getLogger(__name__)

conf_size_adjustment = configured_value("interpolation.size_adjustment", .5)

StateT = TypeVar('StateT')
class Interpolation(Generic[StateT]):
    def get(self, at: float) -> StateT:
        pass

class LayoutDownstreamInterpolation(Interpolation[PyWMDownstreamState]):
    def __init__(self, layout: Layout, state0: PyWMDownstreamState, state1: PyWMDownstreamState) -> None:
        self.lock_perc = (state0.lock_perc, state1.lock_perc)

    def get(self, at: float) -> PyWMDownstreamState:
        at = min(1, max(0, at))
        lock_perc=self.lock_perc[0] + at * (self.lock_perc[1] - self.lock_perc[0])
        if lock_perc < 0.0001:
            lock_perc = 0.0
        return PyWMDownstreamState(lock_perc)

class ViewDownstreamInterpolation(Interpolation[PyWMViewDownstreamState]):
    def __init__(self, layout: Layout, state0: PyWMViewDownstreamState, state1: PyWMViewDownstreamState) -> None:
        self.z_index = (state0.z_index, state1.z_index)
        self.box = (state0.box, state1.box)
        self.mask = (state0.mask, state1.mask)
        self.corner_radius = (state0.corner_radius, state1.corner_radius)
        self.accepts_input = state1.accepts_input
        self.size = (state0.size, state1.size)
        self.opacity = (state0.opacity, state1.opacity)
        self.lock_enabled = state0.lock_enabled
        self.workspace = None
        if state0.workspace is not None and state1.workspace is not None:
            x, y, w, h = state0.workspace
            if state1.workspace[0] < x:
                w += (x - state1.workspace[0])
                x = state1.workspace[0]
            if state1.workspace[1] < y:
                h += (y - state1.workspace[1])
                y = state1.workspace[1]
            if state1.workspace[0] + state1.workspace[2] > x + w:
                w = state1.workspace[0] + state1.workspace[2] - x
            if state1.workspace[1] + state1.workspace[3] > y + h:
                h = state1.workspace[1] + state1.workspace[3] - y
            self.workspace = x, y, w, h

        self.floating = (state0.floating, state1.floating)
        self.fixed_output = (state0.fixed_output, state1.fixed_output)

        self.anim = True
        if self.workspace is not None:
            for ws in layout.workspaces:
                if not ws.prevent_anim:
                    continue
                if ws.pos_x <= self.workspace[0] <= self.workspace[0] + self.workspace[2] <= ws.pos_x + ws.width and \
                   ws.pos_y <= self.workspace[1] <= self.workspace[1] + self.workspace[3] <= ws.pos_y + ws.height:
                    self.anim = False
                    break

        # If the initial window is not visible - trigger (computationally intensive) size change immediately
        # If the final window is not visible - trigger (computationally intensive) size change only afterwards
        self._size_adjustment = conf_size_adjustment()
        if state0.workspace is not None:
            x, y, w, h = state0.box
            ws_x, ws_y, ws_w, ws_h = state0.workspace
            if (x+w - 1. < ws_x) or \
               (y+h - 1. < ws_y) or \
               (ws_x+ws_w - 1. < x) or \
               (ws_y+ws_h - 1. < y):
                self._size_adjustment = 0.
        if state1.workspace is not None:
            x, y, w, h = state1.box
            ws_x, ws_y, ws_w, ws_h = state1.workspace
            if (x+w - 1. < ws_x) or \
               (y+h - 1. < ws_y) or \
               (ws_x+ws_w - 1. < x) or \
               (ws_y+ws_h - 1. < y):
                self._size_adjustment = 0.99

    def get(self, at: float) -> PyWMViewDownstreamState:
        if not self.anim:
            at = 1.

        at = min(1, max(0, at))
        box=(
            self.box[0][0] + (self.box[1][0] - self.box[0][0]) * at,
            self.box[0][1] + (self.box[1][1] - self.box[0][1]) * at,
            self.box[0][2] + (self.box[1][2] - self.box[0][2]) * at,
            self.box[0][3] + (self.box[1][3] - self.box[0][3]) * at,
        )
        mask=(
            self.mask[0][0] + (self.mask[1][0] - self.mask[0][0]) * at,
            self.mask[0][1] + (self.mask[1][1] - self.mask[0][1]) * at,
            self.mask[0][2] + (self.mask[1][2] - self.mask[0][2]) * at,
            self.mask[0][3] + (self.mask[1][3] - self.mask[0][3]) * at,
        )
        res = PyWMViewDownstreamState(
            z_index=self.z_index[1] if at > 0.5 else self.z_index[0],
            box=box,
            mask=mask,
            corner_radius=(self.corner_radius[0] + at * (self.corner_radius[1] - self.corner_radius[0])),
            accepts_input=self.accepts_input
        )

        res.opacity = self.opacity[0] + at * (self.opacity[1] - self.opacity[0])
        res.size=self.size[1] if at > self._size_adjustment else self.size[0]
        res.floating=self.floating[1] if at > self._size_adjustment else self.floating[0]
        res.lock_enabled=self.lock_enabled
        res.workspace=self.workspace
        res.fixed_output=self.fixed_output[1] if at > self._size_adjustment else self.fixed_output[0]
        return res

class WidgetDownstreamInterpolation(Interpolation[PyWMWidgetDownstreamState]):
    def __init__(self, layout: Layout, widget: PyWMWidget, state0: PyWMWidgetDownstreamState, state1: PyWMWidgetDownstreamState) -> None:
        self.z_index = (state0.z_index, state1.z_index)
        self.box = (state0.box, state1.box)
        self.opacity = (state0.opacity, state1.opacity)
        self.lock_enabled = state0.lock_enabled


        self.anim = True
        if widget.output is not None:
            for ws in layout.workspaces:
                if ws.pos_x <= widget.output.pos[0] <= widget.output.pos[0] + widget.output.width <= ws.pos_x + ws.width and \
                    ws.pos_y <= widget.output.pos[1] <= widget.output.pos[1] + widget.output.height <= ws.pos_y + ws.height:
                    if ws.prevent_anim:
                        self.anim = False
                        break

    def get(self, at: float) -> PyWMWidgetDownstreamState:
        if not self.anim:
            at = 1.

        at = min(1, max(0, at))
        box=(
            self.box[0][0] + (self.box[1][0] - self.box[0][0]) * at,
            self.box[0][1] + (self.box[1][1] - self.box[0][1]) * at,
            self.box[0][2] + (self.box[1][2] - self.box[0][2]) * at,
            self.box[0][3] + (self.box[1][3] - self.box[0][3]) * at,
        )
        res = PyWMWidgetDownstreamState(
            z_index=self.z_index[1] if at > 0.5 else self.z_index[0],
            box=box,
        )
        res.opacity = self.opacity[0] + at * (self.opacity[1] - self.opacity[0])
        res.lock_enabled=self.lock_enabled
        return res
