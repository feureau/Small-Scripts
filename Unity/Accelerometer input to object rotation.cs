Accelerometer rotation == rotation of object in game.

transform.rotation = Quaternion.Euler(new Vector3(0, 0, Mathf.Atan2(-Input.acceleration.x, -Input.acceleration.y) * Mathf.Rad2Deg));