#####################################################

# <FLARED is an add-on for Blender that creates lens flare VFX in Eevee.>
# Copyright (C) <2019-2020>  <Beniamino Della Torre e Alfonso Annarumma>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# You can contact the creator of Flared here: blenderlensflare@gmail.com

#####################################################


def flare_particle (obs, context, lensflareprop, suffix):
    sun_beam_number = lensflareprop.sun_beam_number
    iris_number = lensflareprop.iris_number
    obs["IrisParticles"+suffix].particle_systems[0].settings.count = iris_number
    obs["BeamsParticle"+suffix].particle_systems[0].settings.count = sun_beam_number
    
def flare_d_particle (obs, context, lensflareprop, suffix):
    sun_beam_number = lensflareprop.sun_beam_number
    iris_number = lensflareprop.iris_number
    
    obs["BeamsParticle"+suffix].particle_systems[0].settings.count = sun_beam_number